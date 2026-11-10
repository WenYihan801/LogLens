"""Dataset import orchestration: validate -> parse -> normalise -> store -> detect."""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError
from app.database.models import Dataset, ImportErrorRecord, LogEvent, SecurityAlert, utcnow
from app.schemas.dataset import SampleInfo
from app.services.detection.engine import run_detection
from app.services.file_validation import ValidatedFile, validate_upload
from app.services.normaliser import ParseFailure
from app.services.parsers import get_parser

log = logging.getLogger("loglens.datasets")

BATCH_SIZE = 2000
MAX_ERRORS_STORED = 5000  # keep the error table bounded even for very bad files
ERRORS_IN_DETAIL = 200

SAMPLES: dict[str, SampleInfo] = {
    s.key: s
    for s in [
        SampleInfo(
            key="nginx-normal",
            name="Nginx – normal traffic",
            source_type="NGINX",
            filename="nginx/normal_access.log",
            description="Ordinary website traffic. Should not trigger any rule.",
        ),
        SampleInfo(
            key="nginx-suspicious",
            name="Nginx – scanner activity",
            source_type="NGINX",
            filename="nginx/suspicious_access.log",
            description="Normal traffic mixed with a 404 burst and sensitive-path probing.",
        ),
        SampleInfo(
            key="ssh-normal",
            name="SSH – normal logins",
            source_type="SSH",
            filename="ssh/normal_auth.log",
            description="Successful logins and the odd typo. Should not trigger any rule.",
        ),
        SampleInfo(
            key="ssh-bruteforce",
            name="SSH – brute force",
            source_type="SSH",
            filename="ssh/brute_force_sample.log",
            description="Two sources making rapid failed password attempts.",
        ),
    ]
}


def import_dataset(
    db: Session,
    *,
    filename: str | None,
    data: bytes,
    source_type: str | None,
    name: str | None = None,
) -> dict:
    s = get_settings()
    started = time.perf_counter()
    vf = validate_upload(
        filename=filename,
        data=data,
        requested_source=source_type,
        max_bytes=s.max_upload_bytes,
        max_lines=s.max_log_lines,
    )
    duplicate = db.scalar(
        select(Dataset.id)
        .where(Dataset.file_sha256 == vf.sha256, Dataset.source_type == vf.source_type)
        .order_by(Dataset.created_at.desc())
        .limit(1)
    )

    # BR-01: the dataset row is only created once validation passed.
    ds = Dataset(
        name=(name or vf.filename)[:150],
        source_type=vf.source_type,
        original_filename=vf.filename,
        file_sha256=vf.sha256,
        size_bytes=vf.size_bytes,
        total_lines=0,
        parsed_lines=0,
        failed_lines=0,
        status="PROCESSING",
    )
    db.add(ds)
    db.commit()

    try:
        detection = _process(db, ds, vf)
        ds.status = "COMPLETED"
        ds.detection_skipped = detection.skipped_events
        if ds.parsed_lines == 0:
            ds.status_message = "No lines could be parsed. See import errors for details."
        db.commit()
    except Exception as exc:  # pragma: no cover - defensive; tested via monkeypatch
        db.rollback()
        log.exception("Import failed for dataset %s", ds.id)
        ds = db.get(Dataset, ds.id)
        ds.status = "FAILED"
        ds.status_message = f"Processing failed: {type(exc).__name__}"
        db.commit()
        raise AppError(
            500,
            "PROCESSING_FAILED",
            "The file passed validation but processing failed. The dataset was marked FAILED.",
            {"dataset_id": str(ds.id)},
        ) from exc

    return {
        "dataset_id": ds.id,
        "status": ds.status,
        "source_type": ds.source_type,
        "total_lines": ds.total_lines,
        "parsed_lines": ds.parsed_lines,
        "failed_lines": ds.failed_lines,
        "alerts_generated": detection.alerts_total,
        "detection_skipped_events": detection.skipped_events,
        "duplicate_of": duplicate,
        "processing_ms": int((time.perf_counter() - started) * 1000),
    }


def _process(db: Session, ds: Dataset, vf: ValidatedFile):
    parse = get_parser(vf.source_type)
    now = utcnow()
    events: list[dict] = []
    errors: list[dict] = []
    total = parsed = failed = errors_stored = 0

    def flush() -> None:
        nonlocal events, errors
        if events:
            db.execute(insert(LogEvent), events)
            events = []
        if errors:
            db.execute(insert(ImportErrorRecord), errors)
            errors = []

    for idx, line in enumerate(vf.lines, start=1):
        if not line.strip():
            continue  # blank lines are not counted as log lines
        total += 1
        result = parse(line, idx)
        if isinstance(result, ParseFailure):
            failed += 1
            if errors_stored < MAX_ERRORS_STORED:
                errors_stored += 1
                errors.append(
                    {
                        "dataset_id": ds.id,
                        "line_number": result.line_number,
                        "error_code": result.error_code,
                        "error_message": result.error_message,
                        "raw_preview": result.raw_preview,
                        "created_at": now,
                    }
                )
        else:
            parsed += 1
            row = result.as_row()
            row["dataset_id"] = ds.id
            row["created_at"] = now
            events.append(row)
        if len(events) >= BATCH_SIZE or len(errors) >= BATCH_SIZE:
            flush()
    flush()

    ds.total_lines, ds.parsed_lines, ds.failed_lines = total, parsed, failed
    db.flush()
    return run_detection(db, ds.id, ds.source_type)


def rerun_detection(db: Session, dataset_id: uuid.UUID) -> dict:
    ds = get_dataset(db, dataset_id)
    if ds.status != "COMPLETED":
        raise AppError(409, "DATASET_NOT_READY", "Detection can only run on a COMPLETED dataset.")
    res = run_detection(db, ds.id, ds.source_type)
    ds.detection_skipped = res.skipped_events
    db.commit()
    return {
        "dataset_id": ds.id,
        "alerts_total": res.alerts_total,
        "created": res.created,
        "updated": res.updated,
        "removed": res.removed,
        "skipped_events": res.skipped_events,
    }


def _alert_counts(db: Session, ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not ids:
        return {}
    rows = db.execute(
        select(SecurityAlert.dataset_id, func.count())
        .where(SecurityAlert.dataset_id.in_(ids))
        .group_by(SecurityAlert.dataset_id)
    ).all()
    return {r[0]: r[1] for r in rows}


def list_datasets(db: Session) -> list[dict]:
    rows = list(db.scalars(select(Dataset).order_by(Dataset.created_at.desc())))
    counts = _alert_counts(db, [d.id for d in rows])
    return [_to_dict(d, counts.get(d.id, 0)) for d in rows]


def get_dataset(db: Session, dataset_id: uuid.UUID) -> Dataset:
    ds = db.get(Dataset, dataset_id)
    if ds is None:
        raise NotFoundError("dataset", dataset_id)
    return ds


def dataset_detail(db: Session, dataset_id: uuid.UUID) -> dict:
    ds = get_dataset(db, dataset_id)
    counts = _alert_counts(db, [ds.id])
    errors = list(
        db.scalars(
            select(ImportErrorRecord)
            .where(ImportErrorRecord.dataset_id == ds.id)
            .order_by(ImportErrorRecord.line_number)
            .limit(ERRORS_IN_DETAIL + 1)
        )
    )
    summary_rows = db.execute(
        select(ImportErrorRecord.error_code, func.count())
        .where(ImportErrorRecord.dataset_id == ds.id)
        .group_by(ImportErrorRecord.error_code)
    ).all()
    d = _to_dict(ds, counts.get(ds.id, 0))
    d["error_summary"] = {r[0]: r[1] for r in summary_rows}
    d["import_errors"] = errors[:ERRORS_IN_DETAIL]
    d["import_errors_truncated"] = len(errors) > ERRORS_IN_DETAIL
    return d


def delete_dataset(db: Session, dataset_id: uuid.UUID) -> None:
    ds = get_dataset(db, dataset_id)
    # ORM cascade + ON DELETE CASCADE remove events, alerts, evidence, notes, errors (BR-05).
    db.delete(ds)
    db.commit()


def _to_dict(ds: Dataset, alert_count: int) -> dict:
    return {
        "id": ds.id,
        "name": ds.name,
        "source_type": ds.source_type,
        "original_filename": ds.original_filename,
        "file_sha256": ds.file_sha256,
        "size_bytes": ds.size_bytes,
        "total_lines": ds.total_lines,
        "parsed_lines": ds.parsed_lines,
        "failed_lines": ds.failed_lines,
        "detection_skipped": ds.detection_skipped,
        "status": ds.status,
        "status_message": ds.status_message,
        "created_at": ds.created_at,
        "alert_count": alert_count,
    }


# ---------------------------------------------------------------- samples
def sample_path(info: SampleInfo) -> Path:
    base = get_settings().sample_data_dir.resolve()
    path = (base / info.filename).resolve()
    if base not in path.parents:  # defence in depth; keys are a fixed whitelist
        raise AppError(400, "INVALID_SAMPLE", "Invalid sample path.")
    return path


def list_samples() -> list[SampleInfo]:
    return [s for s in SAMPLES.values() if sample_path(s).is_file()]


def import_sample(db: Session, key: str) -> dict:
    info = SAMPLES.get(key)
    if info is None or not sample_path(info).is_file():
        raise AppError(404, "SAMPLE_NOT_FOUND", f"Sample '{key}' is not available on this server.")
    data = sample_path(info).read_bytes()
    return import_dataset(
        db,
        filename=Path(info.filename).name,
        data=data,
        source_type=info.source_type,
        name=info.name,
    )

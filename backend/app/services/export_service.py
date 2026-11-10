"""CSV / JSON exports that honour the current filters (FR-28–FR-30)."""

from __future__ import annotations

import csv
import io
import json
import uuid
from collections.abc import Iterator
from dataclasses import fields
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import AlertEvidence, LogEvent, SecurityAlert
from app.services.alert_service import AlertFilter, alert_to_dict, explanation
from app.services.event_service import EventFilter

EXPORT_EVENT_COLUMNS = [
    "id",
    "dataset_id",
    "event_timestamp",
    "source_type",
    "source_ip",
    "http_method",
    "request_path",
    "status_code",
    "user_agent",
    "username",
    "auth_result",
    "line_number",
    "raw_message",
]

# Cells beginning with these characters can be interpreted as formulas by
# spreadsheet software (CSV/formula injection, OWASP).
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n", "|", "%")


def sanitize_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        v = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    s = str(value)
    if s and (s[0] in _FORMULA_PREFIXES):
        # Numbers like "-1" are safe and common; keep them unchanged.
        try:
            float(s)
            return s
        except ValueError:
            return "'" + s
    return s


def iter_events_csv(db: Session, f: EventFilter, chunk: int = 1000) -> Iterator[str]:
    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
    buf.write("﻿")  # BOM so Excel on macOS/Windows opens UTF-8 correctly
    writer.writerow(EXPORT_EVENT_COLUMNS)
    yield buf.getvalue()
    buf.seek(0)
    buf.truncate()

    stmt = f.apply(select(LogEvent)).order_by(LogEvent.event_timestamp, LogEvent.id)
    for i, ev in enumerate(db.scalars(stmt.execution_options(yield_per=chunk)), start=1):
        writer.writerow([sanitize_cell(getattr(ev, c)) for c in EXPORT_EVENT_COLUMNS])
        if i % chunk == 0:
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate()
    if buf.tell():
        yield buf.getvalue()


def _event_json(ev: LogEvent) -> dict:
    return {c: sanitize_json(getattr(ev, c)) for c in EXPORT_EVENT_COLUMNS}


def sanitize_json(v: object) -> object:
    if isinstance(v, datetime):
        return sanitize_cell(v)
    if isinstance(v, uuid.UUID):
        return str(v)
    return v


def alerts_json(db: Session, f: AlertFilter) -> str:
    alerts = list(
        db.scalars(f.apply(select(SecurityAlert)).order_by(SecurityAlert.first_seen)).unique()
    )
    out = []
    for a in alerts:
        evidence = db.scalars(
            select(LogEvent)
            .join(AlertEvidence, AlertEvidence.log_event_id == LogEvent.id)
            .where(AlertEvidence.alert_id == a.id)
            .order_by(LogEvent.event_timestamp, LogEvent.id)
        )
        d = {k: sanitize_json(v) for k, v in alert_to_dict(a).items()}
        d["rule"] = {
            "rule_code": a.rule.rule_code,
            "name": a.rule.name,
            "threshold": a.rule.threshold,
            "window_seconds": a.rule.window_seconds,
            "version": a.rule.version,
        }
        d["explanation"] = explanation(a)
        d["notes"] = [{"note": n.note, "created_at": sanitize_cell(n.created_at)} for n in a.notes]
        d["evidence"] = [_event_json(e) for e in evidence]
        out.append(d)
    payload = {
        "exported_at": sanitize_cell(datetime.now(timezone.utc)),
        "filters": {fl.name: sanitize_json(getattr(f, fl.name)) for fl in fields(f)},
        "alert_count": len(out),
        "alerts": out,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)

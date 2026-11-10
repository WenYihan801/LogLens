"""Alert queries, status changes and investigation notes (FR-22–FR-27)."""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass

from sqlalchemy import Select, case, func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.database.models import (
    AlertEvidence,
    AlertNote,
    Dataset,
    DetectionRule,
    LogEvent,
    SecurityAlert,
    utcnow,
)

EVIDENCE_LIMIT = 500


@dataclass(slots=True)
class AlertFilter:
    dataset_id: uuid.UUID | None = None
    severity: str | None = None
    status: str | None = None
    source_ip: str | None = None
    rule_code: str | None = None

    def apply(self, stmt: Select) -> Select:
        if self.dataset_id:
            stmt = stmt.where(SecurityAlert.dataset_id == self.dataset_id)
        if self.severity:
            stmt = stmt.where(SecurityAlert.severity == self.severity)
        if self.status:
            stmt = stmt.where(SecurityAlert.status == self.status)
        if self.source_ip:
            stmt = stmt.where(SecurityAlert.source_ip == self.source_ip.strip())
        if self.rule_code:
            stmt = stmt.where(
                SecurityAlert.rule_id.in_(
                    select(DetectionRule.id).where(DetectionRule.rule_code == self.rule_code)
                )
            )
        return stmt


_SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def alert_to_dict(a: SecurityAlert) -> dict:
    return {
        "id": a.id,
        "dataset_id": a.dataset_id,
        "rule_code": a.rule.rule_code,
        "rule_name": a.rule.name,
        "source_ip": a.source_ip,
        "severity": a.severity,
        "status": a.status,
        "occurrence_count": a.occurrence_count,
        "first_seen": a.first_seen,
        "last_seen": a.last_seen,
        "summary": a.summary,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
    }


def list_alerts(db: Session, f: AlertFilter, page: int, page_size: int) -> dict:
    total = db.scalar(f.apply(select(func.count()).select_from(SecurityAlert))) or 0
    sev_rank = case(_SEVERITY_ORDER, value=SecurityAlert.severity, else_=99)
    stmt = (
        f.apply(select(SecurityAlert))
        .order_by(sev_rank, SecurityAlert.first_seen.desc(), SecurityAlert.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [alert_to_dict(a) for a in db.scalars(stmt).unique()]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, math.ceil(total / page_size)),
    }


def _get(db: Session, alert_id: uuid.UUID) -> SecurityAlert:
    a = db.get(SecurityAlert, alert_id)
    if a is None:
        raise NotFoundError("alert", alert_id)
    return a


def explanation(a: SecurityAlert) -> str:
    r = a.rule
    span = int((a.last_seen - a.first_seen).total_seconds())
    return (
        f"Rule {r.rule_code} (v{r.version}) fires when one source IP reaches at least "
        f"{r.threshold} matching events within a {r.window_seconds}-second sliding window. "
        f"Source {a.source_ip} produced {a.occurrence_count} matching events observed over "
        f"{span} seconds. Severity {a.severity}, status {a.status}. "
        "This is a suspicious-behaviour indicator that needs human review — it is not a "
        "confirmed attack. Check the evidence below, the targeted resources or accounts, "
        "and whether the source is expected."
    )


def alert_detail(db: Session, alert_id: uuid.UUID) -> dict:
    a = _get(db, alert_id)
    evidence_total = db.scalar(
        select(func.count()).select_from(AlertEvidence).where(AlertEvidence.alert_id == a.id)
    )
    evidence = list(
        db.scalars(
            select(LogEvent)
            .join(AlertEvidence, AlertEvidence.log_event_id == LogEvent.id)
            .where(AlertEvidence.alert_id == a.id)
            .order_by(LogEvent.event_timestamp, LogEvent.id)
            .limit(EVIDENCE_LIMIT)
        )
    )
    d = alert_to_dict(a)
    d.update(
        dataset_name=db.scalar(select(Dataset.name).where(Dataset.id == a.dataset_id)) or "",
        rule=a.rule,
        explanation=explanation(a),
        observed_window_seconds=int((a.last_seen - a.first_seen).total_seconds()),
        evidence=evidence,
        evidence_total=evidence_total or 0,
        notes=list(a.notes),
    )
    return d


def update_status(db: Session, alert_id: uuid.UUID, status: str) -> dict:
    a = _get(db, alert_id)
    if a.status != status:
        a.status = status
        a.updated_at = utcnow()
        db.commit()
    return alert_to_dict(a)


def add_note(db: Session, alert_id: uuid.UUID, text: str) -> AlertNote:
    a = _get(db, alert_id)
    note = AlertNote(alert_id=a.id, note=text)
    db.add(note)
    a.updated_at = utcnow()  # FR-27: last-modified reflects investigation activity
    db.commit()
    return note


def list_rules(db: Session) -> list[DetectionRule]:
    return list(db.scalars(select(DetectionRule).order_by(DetectionRule.rule_code)))

"""Event search with server-side filtering and pagination (FR-18–FR-21, NFR-03)."""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.database.models import AlertEvidence, Dataset, LogEvent


@dataclass(slots=True)
class EventFilter:
    dataset_id: uuid.UUID | None = None
    source_ip: str | None = None
    source_type: str | None = None
    status_code: int | None = None
    start: datetime | None = None
    end: datetime | None = None
    q: str | None = None  # substring of request path or username

    def apply(self, stmt: Select) -> Select:
        if self.dataset_id:
            stmt = stmt.where(LogEvent.dataset_id == self.dataset_id)
        if self.source_ip:
            stmt = stmt.where(LogEvent.source_ip == self.source_ip.strip())
        if self.source_type:
            stmt = stmt.where(LogEvent.source_type == self.source_type)
        if self.status_code is not None:
            stmt = stmt.where(LogEvent.status_code == self.status_code)
        if self.start:
            stmt = stmt.where(LogEvent.event_timestamp >= self.start)
        if self.end:
            stmt = stmt.where(LogEvent.event_timestamp <= self.end)
        if self.q:
            # ORM parameter binding — no string concatenation into SQL (NFR-05).
            like = f"%{self.q.strip()}%"
            stmt = stmt.where(
                LogEvent.request_path.ilike(like) | LogEvent.username.ilike(like)
            )
        return stmt


def list_events(db: Session, f: EventFilter, page: int, page_size: int) -> dict:
    total = db.scalar(f.apply(select(func.count()).select_from(LogEvent))) or 0
    stmt = (
        f.apply(select(LogEvent))
        .order_by(LogEvent.event_timestamp.desc(), LogEvent.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list(db.scalars(stmt))
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, math.ceil(total / page_size)) if page_size else 1,
    }


def get_event(db: Session, event_id: int) -> dict:
    ev = db.get(LogEvent, event_id)
    if ev is None:
        raise NotFoundError("event", event_id)
    ds_name = db.scalar(select(Dataset.name).where(Dataset.id == ev.dataset_id))
    alert_ids = list(
        db.scalars(select(AlertEvidence.alert_id).where(AlertEvidence.log_event_id == ev.id))
    )
    data = {c.name: getattr(ev, c.name) for c in LogEvent.__table__.columns}
    data["dataset_name"] = ds_name or ""
    data["alert_ids"] = alert_ids
    return data

"""Dashboard aggregations (FR-14–FR-16, BR-09).

Every number is computed with SQL aggregates under the *same* dataset filter so
cards, charts and the alert list always agree.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models import Dataset, LogEvent, SecurityAlert
from app.services.alert_service import alert_to_dict

TOP_N = 10


def _scope(stmt, model, dataset_id: uuid.UUID | None):
    return stmt.where(model.dataset_id == dataset_id) if dataset_id else stmt


def _choose_bucket(start: datetime | None, end: datetime | None) -> str:
    if not start or not end:
        return "hour"
    span = end - start
    if span <= timedelta(hours=3):
        return "minute"
    if span <= timedelta(days=4):
        return "hour"
    return "day"


def _bucket_expr(db: Session, col, bucket: str):
    if db.bind.dialect.name == "postgresql":
        # date_trunc in UTC so buckets are timezone-independent (BR-08).
        return func.date_trunc(bucket, func.timezone("UTC", col))
    fmt = {"minute": "%Y-%m-%dT%H:%M:00", "hour": "%Y-%m-%dT%H:00:00", "day": "%Y-%m-%dT00:00:00"}
    return func.strftime(fmt[bucket], col)


def _as_utc(v) -> datetime:
    if isinstance(v, str):
        v = datetime.fromisoformat(v)
    if v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)
    return v.astimezone(timezone.utc)


def summary(db: Session, dataset_id: uuid.UUID | None) -> dict:
    ev_count = db.scalar(_scope(select(func.count()).select_from(LogEvent), LogEvent, dataset_id)) or 0
    unique_ips = db.scalar(
        _scope(select(func.count(func.distinct(LogEvent.source_ip))), LogEvent, dataset_id)
    ) or 0

    sev_rows = dict(
        db.execute(
            _scope(
                select(SecurityAlert.severity, func.count()).group_by(SecurityAlert.severity),
                SecurityAlert,
                dataset_id,
            )
        ).all()
    )
    status_rows = dict(
        db.execute(
            _scope(
                select(SecurityAlert.status, func.count()).group_by(SecurityAlert.status),
                SecurityAlert,
                dataset_id,
            )
        ).all()
    )

    code_rows = db.execute(
        _scope(
            select(LogEvent.status_code, func.count())
            .where(LogEvent.status_code.is_not(None))
            .group_by(LogEvent.status_code)
            .order_by(LogEvent.status_code),
            LogEvent,
            dataset_id,
        )
    ).all()
    type_rows = db.execute(
        _scope(
            select(LogEvent.source_type, func.count()).group_by(LogEvent.source_type),
            LogEvent,
            dataset_id,
        )
    ).all()
    ip_rows = db.execute(
        _scope(
            select(LogEvent.source_ip, func.count().label("c"))
            .where(LogEvent.source_ip.is_not(None))
            .group_by(LogEvent.source_ip)
            .order_by(func.count().desc(), LogEvent.source_ip)
            .limit(TOP_N),
            LogEvent,
            dataset_id,
        )
    ).all()

    # ---- activity trend
    start, end = db.execute(
        _scope(
            select(func.min(LogEvent.event_timestamp), func.max(LogEvent.event_timestamp)),
            LogEvent,
            dataset_id,
        )
    ).one()
    bucket = _choose_bucket(start and _as_utc(start), end and _as_utc(end))
    ev_bucket = _bucket_expr(db, LogEvent.event_timestamp, bucket).label("b")
    ev_trend = db.execute(
        _scope(select(ev_bucket, func.count()).group_by(ev_bucket).order_by(ev_bucket), LogEvent, dataset_id)
    ).all()
    al_bucket = _bucket_expr(db, SecurityAlert.first_seen, bucket).label("b")
    al_trend = dict(
        (_as_utc(b), c)
        for b, c in db.execute(
            _scope(select(al_bucket, func.count()).group_by(al_bucket), SecurityAlert, dataset_id)
        ).all()
    )
    trend_map: dict[datetime, dict] = {}
    for b, c in ev_trend:
        key = _as_utc(b)
        trend_map[key] = {"bucket": key, "events": c, "alerts": al_trend.get(key, 0)}
    for key, c in al_trend.items():
        trend_map.setdefault(key, {"bucket": key, "events": 0, "alerts": c})
    trend = [trend_map[k] for k in sorted(trend_map)]

    recent = db.scalars(
        _scope(
            select(SecurityAlert).order_by(SecurityAlert.first_seen.desc()).limit(5),
            SecurityAlert,
            dataset_id,
        )
    ).unique()

    dataset_count = db.scalar(
        select(func.count()).select_from(Dataset).where(Dataset.id == dataset_id)
        if dataset_id
        else select(func.count()).select_from(Dataset)
    ) or 0

    total_alerts = sum(sev_rows.values())
    return {
        "dataset_id": str(dataset_id) if dataset_id else None,
        "total_events": ev_count,
        "total_alerts": total_alerts,
        "high_alerts": sev_rows.get("HIGH", 0),
        "medium_alerts": sev_rows.get("MEDIUM", 0),
        "low_alerts": sev_rows.get("LOW", 0),
        "open_alerts": status_rows.get("OPEN", 0),
        "unique_source_ips": unique_ips,
        "dataset_count": dataset_count,
        "severity_distribution": [
            {"key": k, "count": sev_rows.get(k, 0)} for k in ("HIGH", "MEDIUM", "LOW")
        ],
        "alert_status_distribution": [
            {"key": k, "count": status_rows.get(k, 0)} for k in ("OPEN", "ACKNOWLEDGED", "RESOLVED")
        ],
        "status_code_distribution": [{"key": str(k), "count": c} for k, c in code_rows],
        "source_type_distribution": [{"key": k, "count": c} for k, c in type_rows],
        "top_source_ips": [{"key": k, "count": c} for k, c in ip_rows],
        "trend_bucket": bucket,
        "activity_trend": trend,
        "recent_alerts": [alert_to_dict(a) for a in recent],
    }

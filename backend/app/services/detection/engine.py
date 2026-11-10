"""Rule engine: sliding-window detection + idempotent alert persistence.

Algorithm (per rule, per source IP, events sorted by time):

1. Keep a deque of matching events whose timestamps are within ``window_seconds``
   of the newest event (inclusive boundary: ``newest - oldest <= window``).
2. When the deque first reaches ``threshold`` an *episode* opens; its evidence is
   the events currently in the window.
3. While the episode is open, every further matching event that occurs within
   ``window_seconds`` of the episode's last event is appended (the activity is
   still continuing) — so one sustained attack yields one alert, not hundreds.
4. A gap longer than the window closes the episode. A later burst can open a new,
   separate episode/alert.

Each episode's ``dedup_key`` is derived from the dataset, rule, IP and the id of
its first evidence event. Re-running detection on the same dataset therefore
reproduces identical keys: existing alerts are updated in place (keeping their
status and notes), new ones are inserted, and stale ones are removed (FR-12).
"""

from __future__ import annotations

import uuid
from collections import defaultdict, deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database.models import (
    AlertEvidence,
    DetectionRule,
    LogEvent,
    SecurityAlert,
    utcnow,
)
from app.services.detection.rules import (
    DEFAULT_RULES,
    HTTP_404_BURST,
    SENSITIVE_PATH_PROBE,
    SSH_BRUTE_FORCE,
    is_sensitive_path,
)


@dataclass(slots=True, frozen=True)
class EventView:
    """Minimal event projection the engine needs (keeps tests DB-free)."""

    id: int
    ts: datetime
    source_type: str
    source_ip: str | None
    status_code: int | None = None
    request_path: str | None = None
    auth_result: str | None = None


@dataclass(slots=True)
class Episode:
    rule_code: str
    source_ip: str
    events: list[EventView] = field(default_factory=list)

    @property
    def first_seen(self) -> datetime:
        return self.events[0].ts

    @property
    def last_seen(self) -> datetime:
        return self.events[-1].ts


@dataclass(slots=True)
class RuleConfig:
    rule_code: str
    source_type: str
    threshold: int
    window_seconds: int


# Which events count towards each rule.
MATCHERS: dict[str, Callable[[EventView], bool]] = {
    SSH_BRUTE_FORCE: lambda e: e.auth_result == "FAILURE",
    HTTP_404_BURST: lambda e: e.status_code == 404,
    SENSITIVE_PATH_PROBE: lambda e: is_sensitive_path(e.request_path),
}


def find_episodes(events: Iterable[EventView], rule: RuleConfig) -> tuple[list[Episode], int]:
    """Pure function: return (episodes, skipped_count).

    ``skipped_count`` = events of the rule's source type that matched the rule
    condition but had no source IP, so could not be attributed.
    """
    matcher = MATCHERS[rule.rule_code]
    by_ip: dict[str, list[EventView]] = defaultdict(list)
    skipped = 0
    for e in events:
        if e.source_type != rule.source_type or not matcher(e):
            continue
        if not e.source_ip:
            skipped += 1
            continue
        by_ip[e.source_ip].append(e)

    episodes: list[Episode] = []
    for ip in sorted(by_ip):
        evs = sorted(by_ip[ip], key=lambda x: (x.ts, x.id))
        window: deque[EventView] = deque()
        current: Episode | None = None
        for e in evs:
            if current is not None:
                if (e.ts - current.last_seen).total_seconds() <= rule.window_seconds:
                    current.events.append(e)
                    window.append(e)
                    continue
                episodes.append(current)
                current = None
                window.clear()
            window.append(e)
            while (e.ts - window[0].ts).total_seconds() > rule.window_seconds:
                window.popleft()
            if len(window) >= rule.threshold:
                current = Episode(rule.rule_code, ip, list(window))
        if current is not None:
            episodes.append(current)
    return episodes, skipped


def build_summary(rule: DetectionRule, ep: Episode) -> str:
    span = int((ep.last_seen - ep.first_seen).total_seconds())
    what = {
        SSH_BRUTE_FORCE: "failed SSH password attempts",
        HTTP_404_BURST: "HTTP 404 responses",
        SENSITIVE_PATH_PROBE: "requests to sensitive paths",
    }[rule.rule_code]
    return (
        f"{rule.name}: {len(ep.events)} {what} from {ep.source_ip} over {span}s "
        f"(rule: >= {rule.threshold} within {rule.window_seconds}s). "
        "Suspicious activity that requires investigation; not a confirmed attack."
    )


def dedup_key(dataset_id: uuid.UUID, rule_code: str, ep: Episode) -> str:
    return f"{dataset_id}:{rule_code}:{ep.source_ip}:{ep.events[0].id}"


def sync_rules(db: Session) -> None:
    """Insert default rules that do not exist yet. Existing rows are left alone so
    database tuning survives restarts; a higher code version updates defaults."""
    existing = {r.rule_code: r for r in db.scalars(select(DetectionRule))}
    for d in DEFAULT_RULES:
        desc = d.description.format(threshold=d.threshold, window=d.window_seconds)
        row = existing.get(d.rule_code)
        if row is None:
            db.add(
                DetectionRule(
                    rule_code=d.rule_code,
                    name=d.name,
                    description=desc,
                    source_type=d.source_type,
                    threshold=d.threshold,
                    window_seconds=d.window_seconds,
                    severity=d.severity,
                    enabled=True,
                    version=d.version,
                )
            )
        elif row.version < d.version:
            row.name, row.description = d.name, desc
            row.threshold, row.window_seconds = d.threshold, d.window_seconds
            row.severity, row.version = d.severity, d.version
    db.commit()


@dataclass(slots=True)
class DetectionResult:
    alerts_total: int = 0
    created: int = 0
    updated: int = 0
    removed: int = 0
    skipped_events: int = 0


def run_detection(db: Session, dataset_id: uuid.UUID, source_type: str) -> DetectionResult:
    """Run all enabled rules for one dataset inside the caller's transaction."""
    rules = list(
        db.scalars(
            select(DetectionRule).where(
                DetectionRule.enabled.is_(True), DetectionRule.source_type == source_type
            )
        )
    )
    rows = db.execute(
        select(
            LogEvent.id,
            LogEvent.event_timestamp,
            LogEvent.source_type,
            LogEvent.source_ip,
            LogEvent.status_code,
            LogEvent.request_path,
            LogEvent.auth_result,
        ).where(LogEvent.dataset_id == dataset_id)
    ).all()
    events = [EventView(*r) for r in rows]

    existing = {
        a.dedup_key: a
        for a in db.scalars(select(SecurityAlert).where(SecurityAlert.dataset_id == dataset_id))
    }
    result = DetectionResult()
    seen_keys: set[str] = set()

    for rule in rules:
        cfg = RuleConfig(rule.rule_code, rule.source_type, rule.threshold, rule.window_seconds)
        episodes, skipped = find_episodes(events, cfg)
        result.skipped_events += skipped
        for ep in episodes:
            key = dedup_key(dataset_id, rule.rule_code, ep)
            seen_keys.add(key)
            alert = existing.get(key)
            if alert is None:
                alert = SecurityAlert(
                    dataset_id=dataset_id,
                    rule_id=rule.id,
                    status="OPEN",
                    dedup_key=key,
                )
                db.add(alert)
                result.created += 1
            else:
                result.updated += 1
                alert.updated_at = utcnow()
            alert.source_ip = ep.source_ip
            alert.severity = rule.severity
            alert.occurrence_count = len(ep.events)
            alert.first_seen = ep.first_seen
            alert.last_seen = ep.last_seen
            alert.summary = build_summary(rule, ep)
            db.flush()
            # Rebuild evidence links for this alert (composite PK prevents duplicates).
            db.execute(delete(AlertEvidence).where(AlertEvidence.alert_id == alert.id))
            db.add_all(AlertEvidence(alert_id=alert.id, log_event_id=e.id) for e in ep.events)

    for key, alert in existing.items():
        if key not in seen_keys:
            db.delete(alert)
            result.removed += 1

    db.flush()
    result.alerts_total = len(seen_keys)
    return result

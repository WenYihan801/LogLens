"""SQLAlchemy 2.x ORM models — the 7 core tables from SRS §5.3."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# BIGINT autoincrement in PostgreSQL; SQLite only auto-increments INTEGER PKs.
BigIntPK = BigInteger().with_variant(Integer, "sqlite")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# ---- enumerations (stored as VARCHAR for simple, portable migrations) ----
SOURCE_TYPES = ("NGINX", "SSH")
DATASET_STATUSES = ("PENDING", "PROCESSING", "COMPLETED", "FAILED")
SEVERITIES = ("HIGH", "MEDIUM", "LOW")
ALERT_STATUSES = ("OPEN", "ACKNOWLEDGED", "RESOLVED")
AUTH_RESULTS = ("SUCCESS", "FAILURE", "INVALID_USER")


class Dataset(Base):
    __tablename__ = "datasets"
    __table_args__ = (
        CheckConstraint("source_type IN ('NGINX','SSH')", name="ck_datasets_source_type"),
        CheckConstraint(
            "status IN ('PENDING','PROCESSING','COMPLETED','FAILED')", name="ck_datasets_status"
        ),
        Index("ix_datasets_file_sha256", "file_sha256"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_lines: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parsed_lines: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_lines: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Events that rules had to ignore (e.g. missing source IP) — SRS §7.4.
    detection_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    status_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    events: Mapped[list["LogEvent"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan", passive_deletes=True
    )
    alerts: Mapped[list["SecurityAlert"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan", passive_deletes=True
    )
    import_errors: Mapped[list["ImportErrorRecord"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan", passive_deletes=True
    )


class LogEvent(Base):
    __tablename__ = "log_events"
    __table_args__ = (
        Index("ix_log_events_dataset_ts", "dataset_id", "event_timestamp"),
        Index("ix_log_events_source_ip", "source_ip"),
        Index("ix_log_events_status_code", "status_code"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_ip: Mapped[str | None] = mapped_column(String(45))
    http_method: Mapped[str | None] = mapped_column(String(10))
    request_path: Mapped[str | None] = mapped_column(Text)
    status_code: Mapped[int | None] = mapped_column(SmallInteger)
    user_agent: Mapped[str | None] = mapped_column(Text)
    username: Mapped[str | None] = mapped_column(String(120))
    auth_result: Mapped[str | None] = mapped_column(String(20))
    raw_message: Mapped[str] = mapped_column(Text, nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    dataset: Mapped[Dataset] = relationship(back_populates="events")


class DetectionRule(Base):
    __tablename__ = "detection_rules"
    __table_args__ = (
        CheckConstraint("severity IN ('HIGH','MEDIUM','LOW')", name="ck_rules_severity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    rule_code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    window_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


class SecurityAlert(Base):
    __tablename__ = "security_alerts"
    __table_args__ = (
        CheckConstraint("severity IN ('HIGH','MEDIUM','LOW')", name="ck_alerts_severity"),
        CheckConstraint(
            "status IN ('OPEN','ACKNOWLEDGED','RESOLVED')", name="ck_alerts_status"
        ),
        Index("ix_security_alerts_ds_sev_status", "dataset_id", "severity", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("detection_rules.id", ondelete="RESTRICT"), nullable=False
    )
    source_ip: Mapped[str | None] = mapped_column(String(45))
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    dedup_key: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    dataset: Mapped[Dataset] = relationship(back_populates="alerts")
    rule: Mapped[DetectionRule] = relationship(lazy="joined")
    evidence: Mapped[list["AlertEvidence"]] = relationship(
        back_populates="alert", cascade="all, delete-orphan", passive_deletes=True
    )
    notes: Mapped[list["AlertNote"]] = relationship(
        back_populates="alert",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="AlertNote.created_at",
    )


class AlertEvidence(Base):
    __tablename__ = "alert_evidence"

    alert_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("security_alerts.id", ondelete="CASCADE"), primary_key=True
    )
    log_event_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("log_events.id", ondelete="CASCADE"), primary_key=True
    )

    alert: Mapped[SecurityAlert] = relationship(back_populates="evidence")
    event: Mapped[LogEvent] = relationship()


class AlertNote(Base):
    __tablename__ = "alert_notes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    alert_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("security_alerts.id", ondelete="CASCADE"), nullable=False
    )
    note: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    alert: Mapped[SecurityAlert] = relationship(back_populates="notes")


class ImportErrorRecord(Base):
    __tablename__ = "import_errors"
    __table_args__ = (Index("ix_import_errors_ds_line", "dataset_id", "line_number"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    error_code: Mapped[str] = mapped_column(String(60), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    raw_preview: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    dataset: Mapped[Dataset] = relationship(back_populates="import_errors")

import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel, UTCDateTime
from app.schemas.event import EventOut


class RuleOut(ORMModel):
    id: uuid.UUID
    rule_code: str
    name: str
    description: str | None
    source_type: str
    threshold: int
    window_seconds: int
    severity: str
    enabled: bool
    version: int


class AlertOut(ORMModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    rule_code: str
    rule_name: str
    source_ip: str | None
    severity: str
    status: str
    occurrence_count: int
    first_seen: UTCDateTime
    last_seen: UTCDateTime
    summary: str
    created_at: UTCDateTime
    updated_at: UTCDateTime


class NoteOut(ORMModel):
    id: uuid.UUID
    note: str
    created_at: UTCDateTime


class EvidenceEvent(EventOut):
    raw_message: str


class AlertDetail(AlertOut):
    dataset_name: str
    rule: RuleOut
    explanation: str
    observed_window_seconds: int
    evidence: list[EvidenceEvent]
    evidence_total: int
    notes: list[NoteOut]


class StatusUpdate(BaseModel):
    status: Literal["OPEN", "ACKNOWLEDGED", "RESOLVED"]


class NoteCreate(BaseModel):
    note: str = Field(min_length=1, max_length=5000)

    @field_validator("note")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Note cannot be empty")
        return v


__all__ = [
    "AlertDetail",
    "AlertOut",
    "EvidenceEvent",
    "NoteCreate",
    "NoteOut",
    "RuleOut",
    "StatusUpdate",
]

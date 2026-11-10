import uuid

from app.schemas.common import ORMModel, UTCDateTime


class EventOut(ORMModel):
    id: int
    dataset_id: uuid.UUID
    event_timestamp: UTCDateTime
    source_type: str
    source_ip: str | None
    http_method: str | None
    request_path: str | None
    status_code: int | None
    user_agent: str | None
    username: str | None
    auth_result: str | None
    line_number: int


class EventDetail(EventOut):
    raw_message: str
    created_at: UTCDateTime
    dataset_name: str
    alert_ids: list[uuid.UUID]

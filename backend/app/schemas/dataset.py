import uuid

from pydantic import BaseModel

from app.schemas.common import ORMModel, UTCDateTime


class DatasetOut(ORMModel):
    id: uuid.UUID
    name: str
    source_type: str
    original_filename: str
    file_sha256: str
    size_bytes: int
    total_lines: int
    parsed_lines: int
    failed_lines: int
    detection_skipped: int
    status: str
    status_message: str | None
    created_at: UTCDateTime
    alert_count: int = 0


class ImportErrorOut(ORMModel):
    id: int
    line_number: int
    error_code: str
    error_message: str
    raw_preview: str | None


class DatasetDetail(DatasetOut):
    error_summary: dict[str, int]
    import_errors: list[ImportErrorOut]
    import_errors_truncated: bool


class UploadResult(BaseModel):
    dataset_id: uuid.UUID
    status: str
    source_type: str
    total_lines: int
    parsed_lines: int
    failed_lines: int
    alerts_generated: int
    detection_skipped_events: int
    duplicate_of: uuid.UUID | None = None
    processing_ms: int


class DetectionRunResult(BaseModel):
    dataset_id: uuid.UUID
    alerts_total: int
    created: int
    updated: int
    removed: int
    skipped_events: int


class SampleInfo(BaseModel):
    key: str
    name: str
    source_type: str
    filename: str
    description: str

from pydantic import BaseModel

from app.schemas.alert import AlertOut
from app.schemas.common import UTCDateTime


class CountItem(BaseModel):
    key: str
    count: int


class TrendPoint(BaseModel):
    bucket: UTCDateTime
    events: int
    alerts: int


class DashboardSummary(BaseModel):
    dataset_id: str | None
    total_events: int
    total_alerts: int
    high_alerts: int
    medium_alerts: int
    low_alerts: int
    open_alerts: int
    unique_source_ips: int
    dataset_count: int
    severity_distribution: list[CountItem]
    alert_status_distribution: list[CountItem]
    status_code_distribution: list[CountItem]
    source_type_distribution: list[CountItem]
    top_source_ips: list[CountItem]
    trend_bucket: str
    activity_trend: list[TrendPoint]
    recent_alerts: list[AlertOut]

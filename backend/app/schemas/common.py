from datetime import datetime, timezone
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, PlainSerializer

T = TypeVar("T")


def _iso_utc(v: datetime) -> str:
    # SQLite returns naive datetimes; everything we store is UTC (BR-08).
    if v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)
    return v.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


UTCDateTime = Annotated[datetime, PlainSerializer(_iso_utc, return_type=str)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: object | None = None

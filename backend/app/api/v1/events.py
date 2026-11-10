import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import DB, PageNo, PageSize
from app.core.errors import AppError
from app.schemas.common import Page
from app.schemas.event import EventDetail, EventOut
from app.services import event_service
from app.services.event_service import EventFilter

router = APIRouter(prefix="/events", tags=["events"])


def event_filter(
    dataset_id: uuid.UUID | None = None,
    source_ip: Annotated[str | None, Query(max_length=45)] = None,
    source_type: Literal["NGINX", "SSH"] | None = None,
    status_code: Annotated[int | None, Query(ge=100, le=599)] = None,
    start: Annotated[datetime | None, Query(description="ISO 8601, inclusive")] = None,
    end: Annotated[datetime | None, Query(description="ISO 8601, inclusive")] = None,
    q: Annotated[str | None, Query(max_length=200, description="Search path or username")] = None,
) -> EventFilter:
    if start and end and start > end:
        raise AppError(422, "INVALID_TIME_RANGE", "'start' must be earlier than 'end'.")
    return EventFilter(dataset_id, source_ip or None, source_type, status_code, start, end, q or None)


EventFilterDep = Annotated[EventFilter, Depends(event_filter)]


@router.get("", response_model=Page[EventOut])
def list_events(db: DB, f: EventFilterDep, page: PageNo = 1, page_size: PageSize = 50):
    return event_service.list_events(db, f, page, page_size)


@router.get("/{event_id}", response_model=EventDetail)
def get_event(event_id: int, db: DB):
    return event_service.get_event(db, event_id)

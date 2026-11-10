import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DB, PageNo, PageSize
from app.schemas.alert import AlertDetail, AlertOut, NoteCreate, NoteOut, RuleOut, StatusUpdate
from app.schemas.common import Page
from app.services import alert_service
from app.services.alert_service import AlertFilter

router = APIRouter(tags=["alerts"])


def alert_filter(
    dataset_id: uuid.UUID | None = None,
    severity: Literal["HIGH", "MEDIUM", "LOW"] | None = None,
    status: Literal["OPEN", "ACKNOWLEDGED", "RESOLVED"] | None = None,
    source_ip: Annotated[str | None, Query(max_length=45)] = None,
    rule_code: Annotated[str | None, Query(max_length=60)] = None,
) -> AlertFilter:
    return AlertFilter(dataset_id, severity, status, source_ip or None, rule_code or None)


AlertFilterDep = Annotated[AlertFilter, Depends(alert_filter)]


@router.get("/alerts", response_model=Page[AlertOut])
def list_alerts(db: DB, f: AlertFilterDep, page: PageNo = 1, page_size: PageSize = 50):
    return alert_service.list_alerts(db, f, page, page_size)


@router.get("/alerts/{alert_id}", response_model=AlertDetail)
def get_alert(alert_id: uuid.UUID, db: DB):
    return alert_service.alert_detail(db, alert_id)


@router.patch("/alerts/{alert_id}/status", response_model=AlertOut)
def update_status(alert_id: uuid.UUID, body: StatusUpdate, db: DB):
    return alert_service.update_status(db, alert_id, body.status)


@router.post(
    "/alerts/{alert_id}/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED
)
def add_note(alert_id: uuid.UUID, body: NoteCreate, db: DB):
    return alert_service.add_note(db, alert_id, body.note)


@router.get("/rules", response_model=list[RuleOut], tags=["rules"])
def list_rules(db: DB):
    return alert_service.list_rules(db)

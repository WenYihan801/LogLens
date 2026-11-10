import uuid

from fastapi import APIRouter

from app.api.deps import DB
from app.schemas.dashboard import DashboardSummary
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def summary(db: DB, dataset_id: uuid.UUID | None = None):
    return dashboard_service.summary(db, dataset_id)

from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import Response, StreamingResponse

from app.api.deps import DB
from app.api.v1.alerts import AlertFilterDep
from app.api.v1.events import EventFilterDep
from app.services import export_service

router = APIRouter(prefix="/exports", tags=["exports"])


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


@router.get("/events.csv", response_class=StreamingResponse)
def export_events_csv(db: DB, f: EventFilterDep):
    return StreamingResponse(
        export_service.iter_events_csv(db, f),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="loglens-events-{_stamp()}.csv"'},
    )


@router.get("/alerts.json")
def export_alerts_json(db: DB, f: AlertFilterDep):
    return Response(
        export_service.alerts_json(db, f),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="loglens-alerts-{_stamp()}.json"'},
    )

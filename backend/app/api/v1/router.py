from fastapi import APIRouter, Request

from app.api.v1 import alerts, dashboard, datasets, events, exports
from app.core.config import get_settings

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(datasets.router)
api_router.include_router(events.router)
api_router.include_router(alerts.router)
api_router.include_router(dashboard.router)
api_router.include_router(exports.router)


@api_router.get("/config", tags=["meta"])
def public_config(request: Request):
    """Non-secret runtime settings the frontend needs (e.g. hide write buttons)."""
    s = get_settings()
    return {
        "app_env": s.app_env,
        "read_only": request.app.state.read_only,
        "max_upload_size_mb": s.max_upload_size_mb,
        "max_log_lines": s.max_log_lines,
    }

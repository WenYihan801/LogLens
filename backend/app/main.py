"""FastAPI application factory."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app import __version__
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import error_body, register_error_handlers
from app.database import connection
from app.services.detection.engine import sync_rules

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Seed / upgrade rule definitions (schema itself is managed by Alembic).
    with connection.SessionLocal() as db:
        try:
            sync_rules(db)
        except Exception:  # pragma: no cover - DB not migrated yet
            logging.getLogger("loglens").warning(
                "Could not sync detection rules. Did you run 'alembic upgrade head'?"
            )
    yield


def create_app() -> FastAPI:
    s = get_settings()
    logging.basicConfig(level=s.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    app = FastAPI(
        title="LogLens API",
        version=__version__,
        description="Lightweight log analysis and security event detection platform.",
        lifespan=lifespan,
    )
    app.state.read_only = s.demo_read_only

    @app.middleware("http")
    async def read_only_guard(request: Request, call_next):
        # FR-33 / BR-07 / NFR-08: enforced on the server, not just hidden in the UI.
        if (
            request.app.state.read_only
            and request.method in WRITE_METHODS
            and request.url.path.startswith("/api/")
        ):
            return JSONResponse(
                status_code=403,
                content=error_body(
                    "DEMO_READ_ONLY",
                    "This public demo is read-only. Run LogLens locally to upload logs or change alerts.",
                ),
            )
        return await call_next(request)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        resp = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        return resp

    # Added last so it is the outermost middleware: CORS headers are also present on 403s.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type"],
        expose_headers=["Content-Disposition"],
    )

    register_error_handlers(app)
    app.include_router(api_router)

    @app.get("/health", tags=["meta"])
    def health():
        db_ok = True
        try:
            with connection.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception:
            db_ok = False
        body = {
            "status": "ok" if db_ok else "degraded",
            "database": "ok" if db_ok else "unavailable",
            "version": __version__,
            "read_only": app.state.read_only,
        }
        return JSONResponse(body, status_code=200 if db_ok else 503)

    return app


app = create_app()

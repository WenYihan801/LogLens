"""Test fixtures.

* Set ``TEST_DATABASE_URL`` (e.g. postgresql+psycopg://loglens:loglens@localhost:5432/loglens_test)
  to run the integration tests against PostgreSQL — recommended, and what CI does.
* Without it, a temporary SQLite file is used so the suite runs anywhere.
"""

import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="loglens-test-"))
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", f"sqlite:///{_tmp / 'test.db'}")
os.environ["DEMO_READ_ONLY"] = "false"
os.environ["UPLOAD_RATE_LIMIT_PER_MINUTE"] = "0"
os.environ["SSH_LOG_YEAR"] = "2026"
os.environ["SSH_LOG_TIMEZONE"] = "UTC"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.database.connection import SessionLocal, engine  # noqa: E402
from app.database.models import Base  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services.detection.engine import sync_rules  # noqa: E402

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "sample_data"
TABLES = [
    "alert_notes",
    "alert_evidence",
    "security_alerts",
    "import_errors",
    "log_events",
    "datasets",
    "detection_rules",
]


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _clean_db():
    with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            conn.execute(text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE"))
        else:
            for t in TABLES:
                conn.execute(text(f"DELETE FROM {t}"))
    with SessionLocal() as db:
        sync_rules(db)
    yield


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client():
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()


@pytest.fixture
def read_only_client(monkeypatch):
    monkeypatch.setenv("DEMO_READ_ONLY", "true")
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        yield c
    monkeypatch.setenv("DEMO_READ_ONLY", "false")
    get_settings.cache_clear()


def upload(client, content: bytes | str, filename="test.log", source_type="AUTO"):
    if isinstance(content, str):
        content = content.encode()
    return client.post(
        "/api/v1/datasets/upload",
        files={"file": (filename, content, "text/plain")},
        data={"source_type": source_type},
    )

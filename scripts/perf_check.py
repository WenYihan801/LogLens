#!/usr/bin/env python3
"""Measure NFR-01 / NFR-02 on your machine and print a line for the README.

Uses TEST_DATABASE_URL (a disposable database — tables are dropped afterwards).
    cd backend && TEST_DATABASE_URL=postgresql+psycopg://loglens:loglens@localhost:5432/loglens_test \
        .venv/bin/python ../scripts/perf_check.py
"""

import logging
import os
import platform
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://loglens:loglens@localhost:5432/loglens_test"
)
os.environ["UPLOAD_RATE_LIMIT_PER_MINUTE"] = "0"
os.environ["LOG_LEVEL"] = "WARNING"

from fastapi.testclient import TestClient  # noqa: E402

from app.database.connection import engine  # noqa: E402
from app.database.models import Base  # noqa: E402
from app.main import create_app  # noqa: E402

logging.getLogger("httpx").setLevel(logging.WARNING)


def main() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    src = (ROOT / "sample_data/nginx/suspicious_access.log").read_text().splitlines()
    lines: list[str] = []
    while len(lines) < 20_000:
        lines += src
    data = ("\n".join(lines[:20_000]) + "\n").encode()

    try:
        with TestClient(create_app()) as c:
            t = time.perf_counter()
            r = c.post("/api/v1/datasets/upload", files={"file": ("big.log", data)}, data={"source_type": "NGINX"})
            import_s = time.perf_counter() - t
            r.raise_for_status()
            times = []
            for _ in range(30):
                t = time.perf_counter()
                c.get("/api/v1/dashboard/summary").raise_for_status()
                times.append(time.perf_counter() - t)
            times.sort()
            t = time.perf_counter()
            page = c.get("/api/v1/events", params={"page_size": 50}).json()
            events_ms = (time.perf_counter() - t) * 1000
    finally:
        Base.metadata.drop_all(engine)

    print(f"Machine       : {platform.platform()} / {platform.machine()} / Python {platform.python_version()}")
    print(f"Import        : 20,000 lines, {len(data) / 1024 / 1024:.1f} MB -> {import_s:.2f} s  (target <= 30 s)")
    print(f"Dashboard     : median {statistics.median(times) * 1000:.0f} ms, p95 {times[int(len(times) * 0.95) - 1] * 1000:.0f} ms  (target <= 2 s)")
    print(f"Events page   : {events_ms:.0f} ms, {len(page['items'])} of {page['total']} rows returned")


if __name__ == "__main__":
    main()

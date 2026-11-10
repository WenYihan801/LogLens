"""Public demo must be read-only on the *server* (FR-33, AC-13)."""

from tests.conftest import upload


def test_writes_rejected_in_read_only_mode(client, read_only_client):
    # Seed data with the normal client first.
    ds = client.post("/api/v1/datasets/samples/ssh-bruteforce").json()["dataset_id"]
    alert_id = client.get("/api/v1/alerts").json()["items"][0]["id"]

    ro = read_only_client
    calls = [
        lambda: upload(ro, "x", "a.log"),
        lambda: ro.post("/api/v1/datasets/samples/ssh-normal"),
        lambda: ro.delete(f"/api/v1/datasets/{ds}"),
        lambda: ro.post(f"/api/v1/datasets/{ds}/detect"),
        lambda: ro.patch(f"/api/v1/alerts/{alert_id}/status", json={"status": "RESOLVED"}),
        lambda: ro.post(f"/api/v1/alerts/{alert_id}/notes", json={"note": "hi"}),
        lambda: ro.put(f"/api/v1/alerts/{alert_id}/status", json={"status": "RESOLVED"}),
    ]
    for call in calls:
        r = call()
        assert r.status_code == 403, r.text
        assert r.json()["error_code"] == "DEMO_READ_ONLY"

    # Nothing changed
    assert len(ro.get("/api/v1/datasets").json()) == 1
    a = ro.get(f"/api/v1/alerts/{alert_id}").json()
    assert a["status"] == "OPEN" and a["notes"] == []


def test_reads_allowed_in_read_only_mode(read_only_client):
    ro = read_only_client
    assert ro.get("/api/v1/config").json()["read_only"] is True
    for path in ["/health", "/api/v1/datasets", "/api/v1/events", "/api/v1/alerts",
                 "/api/v1/dashboard/summary", "/api/v1/exports/events.csv", "/api/v1/exports/alerts.json"]:
        assert ro.get(path).status_code == 200, path


def test_cors_only_allows_configured_origin(client):
    ok = client.options(
        "/api/v1/datasets",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.options(
        "/api/v1/datasets",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in bad.headers


def test_upload_rate_limit(monkeypatch):
    from app.api.v1 import datasets

    limiter = datasets.upload_limiter
    old = limiter.limit
    limiter.limit = 2
    limiter.reset()
    try:
        from fastapi.testclient import TestClient

        from app.main import create_app

        with TestClient(create_app()) as c:
            codes = [upload(c, "hello", "a.log").status_code for _ in range(3)]
        assert codes[:2] != [429, 429] and codes[2] == 429
    finally:
        limiter.limit = old
        limiter.reset()

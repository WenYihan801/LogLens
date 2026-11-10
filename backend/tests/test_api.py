"""API integration tests: upload -> parse -> store -> detect -> query -> export."""

import csv
import io
import json

from sqlalchemy import func, select

from app.database.models import (
    AlertEvidence,
    AlertNote,
    Dataset,
    ImportErrorRecord,
    LogEvent,
    SecurityAlert,
)
from tests.conftest import SAMPLE_DIR, upload


def _sample(rel: str) -> bytes:
    return (SAMPLE_DIR / rel).read_bytes()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


# ---------------------------------------------------------------- upload & validation
def test_upload_nginx_suspicious_end_to_end(client, db):
    r = upload(client, _sample("nginx/suspicious_access.log"), "suspicious_access.log", "NGINX")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "COMPLETED" and body["source_type"] == "NGINX"
    assert body["parsed_lines"] + body["failed_lines"] == body["total_lines"]
    assert body["failed_lines"] == 3  # bad month, bad IP, free text
    assert body["alerts_generated"] == 2

    # AC-03: stored in DB, counts consistent
    ds_id = body["dataset_id"]
    assert db.scalar(select(func.count()).select_from(LogEvent)) == body["parsed_lines"]
    assert db.scalar(select(func.count()).select_from(ImportErrorRecord)) == 3

    alerts = client.get("/api/v1/alerts", params={"dataset_id": ds_id}).json()["items"]
    by_rule = {a["rule_code"]: a for a in alerts}
    assert set(by_rule) == {"HTTP_404_BURST", "SENSITIVE_PATH_PROBE"}
    assert by_rule["HTTP_404_BURST"]["source_ip"] == "203.0.113.45"
    assert by_rule["SENSITIVE_PATH_PROBE"]["source_ip"] == "198.51.100.23"
    assert all(a["status"] == "OPEN" for a in alerts)


def test_upload_ssh_bruteforce_autodetect(client):
    r = upload(client, _sample("ssh/brute_force_sample.log"), "auth.log")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["source_type"] == "SSH"
    alerts = client.get("/api/v1/alerts", params={"dataset_id": body["dataset_id"]}).json()["items"]
    ips = sorted(a["source_ip"] for a in alerts)
    # 198.51.100.77 stays below threshold (negative case)
    assert ips == ["2001:db8:bad::7", "203.0.113.99"]
    assert all(a["severity"] == "HIGH" and a["rule_code"] == "SSH_BRUTE_FORCE" for a in alerts)


def test_normal_samples_trigger_nothing(client):
    for rel, st in [("nginx/normal_access.log", "NGINX"), ("ssh/normal_auth.log", "SSH")]:
        r = upload(client, _sample(rel), rel.split("/")[1], st)
        assert r.status_code == 201
        assert r.json()["alerts_generated"] == 0


def test_bad_lines_do_not_abort_import(client):
    good = '192.0.2.1 - - [03/Nov/2026:10:00:00 +0000] "GET / HTTP/1.1" 200 1 "-" "-"'
    content = "\n".join([good, "garbage", good, "", "more garbage", good]) + "\n"
    r = upload(client, content, "x.log", "NGINX")
    assert r.status_code == 201
    b = r.json()
    assert (b["total_lines"], b["parsed_lines"], b["failed_lines"]) == (5, 3, 2)
    detail = client.get(f"/api/v1/datasets/{b['dataset_id']}").json()
    assert [e["line_number"] for e in detail["import_errors"]] == [2, 5]
    assert detail["error_summary"] == {"NGINX_FORMAT_MISMATCH": 2}


def test_reject_wrong_extension(client):
    r = upload(client, "x", "evil.exe")
    assert r.status_code == 400 and r.json()["error_code"] == "UNSUPPORTED_FILE_TYPE"


def test_reject_empty(client):
    r = upload(client, b"", "a.log")
    assert r.json()["error_code"] == "EMPTY_FILE"
    r = upload(client, b"\n\n  \n", "a.log")
    assert r.json()["error_code"] == "EMPTY_FILE"


def test_reject_binary_disguised_as_log(client):
    r = upload(client, b"\x1f\x8b\x08\x00" + bytes(range(256)) * 10, "access.log")
    assert r.status_code == 400 and r.json()["error_code"] == "BINARY_FILE"


def test_reject_bad_encoding(client):
    r = upload(client, "café".encode("latin-1") * 100, "a.log")
    assert r.status_code == 400 and r.json()["error_code"] == "INVALID_ENCODING"


def test_reject_too_large(client):
    r = upload(client, b"a" * (5 * 1024 * 1024 + 1), "a.log")
    assert r.status_code == 413 and r.json()["error_code"] == "FILE_TOO_LARGE"


def test_reject_too_many_lines(client):
    r = upload(client, "x\n" * 20_001, "a.log")
    assert r.status_code == 413 and r.json()["error_code"] == "TOO_MANY_LINES"


def test_reject_format_mismatch(client):
    r = upload(client, _sample("ssh/normal_auth.log"), "a.log", "NGINX")
    assert r.status_code == 422
    body = r.json()
    assert body["error_code"] == "FORMAT_MISMATCH"
    assert body["details"]["suggested_source_type"] == "SSH"


def test_reject_unrecognised(client):
    r = upload(client, "hello\nworld\n", "a.txt")
    assert r.status_code == 422 and r.json()["error_code"] == "UNRECOGNISED_FORMAT"


def test_duplicate_upload_is_flagged(client):
    first = upload(client, _sample("ssh/normal_auth.log"), "a.log").json()
    second = upload(client, _sample("ssh/normal_auth.log"), "a.log").json()
    assert second["duplicate_of"] == first["dataset_id"]


def test_path_traversal_filename_is_sanitised(client):
    r = upload(client, _sample("ssh/normal_auth.log"), "../../etc/passwd.log")
    ds = client.get(f"/api/v1/datasets/{r.json()['dataset_id']}").json()
    assert ds["original_filename"] == "passwd.log"


# ---------------------------------------------------------------- datasets
def test_dataset_list_detail_and_cascade_delete(client, db):
    ds_id = upload(client, _sample("ssh/brute_force_sample.log"), "a.log").json()["dataset_id"]
    alert_id = client.get("/api/v1/alerts").json()["items"][0]["id"]
    client.post(f"/api/v1/alerts/{alert_id}/notes", json={"note": "check"})

    lst = client.get("/api/v1/datasets").json()
    assert len(lst) == 1 and lst[0]["alert_count"] == 2

    assert client.delete(f"/api/v1/datasets/{ds_id}").status_code == 204
    for model in (Dataset, LogEvent, SecurityAlert, AlertEvidence, AlertNote, ImportErrorRecord):
        assert db.scalar(select(func.count()).select_from(model)) == 0, model.__name__
    assert client.get(f"/api/v1/datasets/{ds_id}").status_code == 404


def test_rerun_detection_endpoint_is_idempotent(client):
    ds_id = upload(client, _sample("ssh/brute_force_sample.log"), "a.log").json()["dataset_id"]
    r1 = client.post(f"/api/v1/datasets/{ds_id}/detect").json()
    r2 = client.post(f"/api/v1/datasets/{ds_id}/detect").json()
    assert r1["alerts_total"] == r2["alerts_total"] == 2
    assert r1["created"] == r2["created"] == 0
    assert client.get("/api/v1/alerts").json()["total"] == 2


def test_samples_endpoint(client):
    keys = {s["key"] for s in client.get("/api/v1/datasets/samples").json()}
    assert keys == {"nginx-normal", "nginx-suspicious", "ssh-normal", "ssh-bruteforce"}
    r = client.post("/api/v1/datasets/samples/ssh-bruteforce")
    assert r.status_code == 201 and r.json()["alerts_generated"] == 2
    assert client.post("/api/v1/datasets/samples/nope").status_code == 404


# ---------------------------------------------------------------- events
def test_event_filtering_and_pagination(client):
    ds_id = upload(client, _sample("nginx/suspicious_access.log"), "s.log", "NGINX").json()["dataset_id"]
    r = client.get("/api/v1/events", params={"dataset_id": ds_id, "source_ip": "203.0.113.45", "page_size": 10})
    body = r.json()
    assert body["total"] == 36 and body["pages"] == 4 and len(body["items"]) == 10
    last = client.get("/api/v1/events", params={"source_ip": "203.0.113.45", "page_size": 10, "page": 4}).json()
    assert len(last["items"]) == 6
    beyond = client.get("/api/v1/events", params={"source_ip": "203.0.113.45", "page_size": 10, "page": 9}).json()
    assert beyond["items"] == [] and beyond["total"] == 36

    only_404 = client.get("/api/v1/events", params={"status_code": 404, "page_size": 200}).json()
    assert only_404["total"] >= 36 and all(e["status_code"] == 404 for e in only_404["items"])

    ranged = client.get(
        "/api/v1/events",
        params={"start": "2026-11-03T10:14:00Z", "end": "2026-11-03T10:16:30Z", "source_ip": "203.0.113.45"},
    ).json()
    assert ranged["total"] == 36

    none = client.get("/api/v1/events", params={"source_ip": "192.0.2.254"}).json()
    assert none["total"] == 0 and none["items"] == []

    q = client.get("/api/v1/events", params={"q": "wp-login"}).json()
    assert q["total"] >= 2


def test_event_page_size_capped(client):
    assert client.get("/api/v1/events", params={"page_size": 10_000}).status_code == 422


def test_invalid_time_range(client):
    r = client.get("/api/v1/events", params={"start": "2026-11-04T00:00:00Z", "end": "2026-11-03T00:00:00Z"})
    assert r.status_code == 422 and r.json()["error_code"] == "INVALID_TIME_RANGE"


def test_event_detail(client):
    upload(client, _sample("ssh/brute_force_sample.log"), "a.log")
    ev = client.get("/api/v1/events", params={"source_ip": "203.0.113.99", "page_size": 1}).json()["items"][0]
    d = client.get(f"/api/v1/events/{ev['id']}").json()
    assert "raw_message" in d and d["event_timestamp"].endswith("Z")
    assert client.get("/api/v1/events/999999999").status_code == 404


# ---------------------------------------------------------------- alerts
def test_alert_detail_status_and_notes(client):
    upload(client, _sample("ssh/brute_force_sample.log"), "a.log")
    alert = client.get("/api/v1/alerts", params={"source_ip": "203.0.113.99"}).json()["items"][0]
    d = client.get(f"/api/v1/alerts/{alert['id']}").json()
    assert d["rule"]["threshold"] == 5 and d["rule"]["window_seconds"] == 300
    assert d["evidence_total"] == alert["occurrence_count"] == len(d["evidence"])
    assert all(e["source_ip"] == "203.0.113.99" and e["auth_result"] == "FAILURE" for e in d["evidence"])
    assert "not a confirmed attack" in d["explanation"]

    r = client.patch(f"/api/v1/alerts/{alert['id']}/status", json={"status": "ACKNOWLEDGED"})
    assert r.status_code == 200 and r.json()["status"] == "ACKNOWLEDGED"
    assert r.json()["updated_at"] >= alert["updated_at"]
    assert client.patch(f"/api/v1/alerts/{alert['id']}/status", json={"status": "BOGUS"}).status_code == 422

    n = client.post(f"/api/v1/alerts/{alert['id']}/notes", json={"note": "  <script>alert(1)</script>  "})
    assert n.status_code == 201 and n.json()["note"] == "<script>alert(1)</script>"  # stored as text
    assert client.post(f"/api/v1/alerts/{alert['id']}/notes", json={"note": "   "}).status_code == 422

    filt = client.get("/api/v1/alerts", params={"status": "ACKNOWLEDGED"}).json()
    assert filt["total"] == 1
    assert client.get("/api/v1/alerts", params={"rule_code": "HTTP_404_BURST"}).json()["total"] == 0
    assert client.get("/api/v1/alerts", params={"severity": "HIGH"}).json()["total"] == 2


def test_rules_endpoint(client):
    codes = {r["rule_code"] for r in client.get("/api/v1/rules").json()}
    assert codes == {"SSH_BRUTE_FORCE", "HTTP_404_BURST", "SENSITIVE_PATH_PROBE"}


# ---------------------------------------------------------------- dashboard (AC-07)
def test_dashboard_matches_database(client, db):
    a = upload(client, _sample("nginx/suspicious_access.log"), "s.log", "NGINX").json()["dataset_id"]
    upload(client, _sample("ssh/brute_force_sample.log"), "b.log", "SSH")

    total = client.get("/api/v1/dashboard/summary").json()
    assert total["total_events"] == db.scalar(select(func.count()).select_from(LogEvent))
    assert total["total_alerts"] == db.scalar(select(func.count()).select_from(SecurityAlert)) == 4
    assert total["high_alerts"] == 2 and total["medium_alerts"] == 2
    assert total["unique_source_ips"] == db.scalar(select(func.count(func.distinct(LogEvent.source_ip))))
    assert total["dataset_count"] == 2

    scoped = client.get("/api/v1/dashboard/summary", params={"dataset_id": a}).json()
    assert scoped["total_alerts"] == 2 and scoped["high_alerts"] == 0
    assert sum(p["events"] for p in scoped["activity_trend"]) == scoped["total_events"]
    assert sum(c["count"] for c in scoped["status_code_distribution"]) == scoped["total_events"]
    assert scoped["top_source_ips"][0]["key"] == "203.0.113.45"
    assert {s["key"] for s in scoped["source_type_distribution"]} == {"NGINX"}


def test_dashboard_empty(client):
    s = client.get("/api/v1/dashboard/summary").json()
    assert s["total_events"] == 0 and s["activity_trend"] == [] and s["recent_alerts"] == []


# ---------------------------------------------------------------- exports (AC-10)
def test_csv_export_respects_filters_and_escapes(client):
    ds = upload(client, _sample("nginx/suspicious_access.log"), "s.log", "NGINX").json()["dataset_id"]
    r = client.get("/api/v1/exports/events.csv", params={"dataset_id": ds, "source_ip": "203.0.113.45"})
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(r.text.lstrip("﻿"))))
    assert len(rows) == 36 and {row["source_ip"] for row in rows} == {"203.0.113.45"}

    r = client.get("/api/v1/exports/events.csv", params={"source_ip": "192.0.2.79"})
    row = next(csv.DictReader(io.StringIO(r.text.lstrip("﻿"))))
    assert row["user_agent"].startswith("'=")  # formula neutralised


def test_json_export_includes_evidence(client):
    upload(client, _sample("ssh/brute_force_sample.log"), "a.log")
    r = client.get("/api/v1/exports/alerts.json", params={"source_ip": "203.0.113.99"})
    data = json.loads(r.text)
    assert data["alert_count"] == 1
    a = data["alerts"][0]
    assert len(a["evidence"]) == a["occurrence_count"] and a["rule"]["rule_code"] == "SSH_BRUTE_FORCE"
    assert data["filters"]["source_ip"] == "203.0.113.99"


def test_unified_error_shape(client):
    r = client.get("/api/v1/alerts/not-a-uuid")
    assert r.status_code == 422 and set(r.json()) >= {"error_code", "message"}
    r = client.get("/api/v1/alerts/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404 and r.json()["error_code"] == "ALERT_NOT_FOUND"

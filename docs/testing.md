# Testing

| Layer | Tool | Count | Command |
|---|---|---|---|
| Unit – parsers, normaliser, rules, sliding window | Pytest | 67 | `make test-backend` |
| Integration – API + DB + migrations | Pytest + SQLite **or** PostgreSQL | 33 | `make test-backend-pg` |
| Frontend – components, pages, URL state | Vitest + Testing Library | 23 | `make test-frontend` |
| End-to-end – full user journey | Playwright | 2 | `make e2e` |

All 100 backend tests pass on both SQLite and PostgreSQL 16. CI (`.github/workflows/ci.yml`) also runs `alembic upgrade → check → downgrade`, lint and type checks, and a Docker Compose smoke test including the read-only check.

## Measured performance (NFR-01, NFR-02)

Measured with `make perf` (`scripts/perf_check.py`): 20,000 Nginx lines (3.5 MB) imported through the API into PostgreSQL 16, then 30 dashboard requests.

| Environment | Import 20k lines | Dashboard median / p95 | Events page (50 rows) |
|---|---|---|---|
| Linux x86_64 VM, 2 vCPU Xeon 2.1 GHz, Python 3.13, PostgreSQL 16 (local) | **2.3 s** (target ≤ 30 s) | **48 ms / 54 ms** (target ≤ 2 s) | 17 ms |
| *Your Mac — run `make perf` and add the line here* | | | |

These figures are for this specific setup and are not a performance guarantee.

## Requirement traceability (acceptance criteria)

| AC | Requirement | Verified by |
|---|---|---|
| AC-01 | Valid Nginx log uploads and imports | `test_upload_nginx_suspicious_end_to_end` |
| AC-02 | SSH sample recognised | `test_upload_ssh_bruteforce_autodetect`, `TestSSHParser` |
| AC-03 | Parsed records stored in PostgreSQL | `test_upload_nginx_suspicious_end_to_end` (row counts), run with `make test-backend-pg` |
| AC-04 | Bad lines recorded, import continues | `test_bad_lines_do_not_abort_import` |
| AC-05 | All three rules triggerable | `test_upload_nginx_suspicious_end_to_end`, `test_upload_ssh_bruteforce_autodetect`, `test_detection.py` |
| AC-06 | Alerts show basis and evidence | `test_alert_detail_status_and_notes`, Vitest `AlertDetailPage`, Playwright |
| AC-07 | Dashboard equals DB queries | `test_dashboard_matches_database` |
| AC-08 | Event filters and pagination | `test_event_filtering_and_pagination`, Vitest `EventsPage`, Playwright |
| AC-09 | Status change and notes (local) | `test_alert_detail_status_and_notes`, Playwright |
| AC-10 | Exports respect scope | `test_csv_export_respects_filters_and_escapes`, `test_json_export_includes_evidence`, Playwright download check |
| AC-11 | Docker Compose starts the system | CI `docker` job |
| AC-12 | Public demo shows samples | `make demo`; `test_reads_allowed_in_read_only_mode` |
| AC-13 | Demo cannot write | `test_writes_rejected_in_read_only_mode` (7 write calls → 403, data unchanged), CI `docker` job |
| AC-14 | Automated tests for parsers, rules, APIs | this document |
| AC-15 | English README | [`README.md`](../README.md) |

## Edge cases covered (SRS §11.3)

* **Files:** empty, whitespace-only, > 5 MB, > 20,000 lines, binary disguised as `.log`, Latin-1 encoding, wrong extension, unrecognised format, format/type mismatch, duplicate upload, path-traversal filename.
* **Lines:** missing IP (`-`), invalid IP, IPv6, IPv4-mapped IPv6, invalid month, missing timezone, invalid status code, escaped quotes, 10,000-char User-Agent, TLS garbage request, CSV formula payload, HTML in note text and usernames.
* **Rules:** threshold − 1 / exact / sustained, 300 s vs 301 s boundary, unsorted input, two bursts, different IPs, cross-dataset, different rules on same IP, disabled rule, tightened threshold.
* **API:** last page, page beyond end, no results, page_size cap, invalid time range, invalid UUID, unknown IDs, invalid status value, empty note.
* **Demo mode:** direct POST/PUT/PATCH/DELETE calls rejected server-side; CORS rejects unknown origin; upload rate limit returns 429.
* **Frontend:** API unreachable message, empty state, read-only controls disabled, untrusted text never rendered as HTML.

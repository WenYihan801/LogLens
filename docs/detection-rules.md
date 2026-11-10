# Detection rules

Rules are **explainable**: each alert stores the rule, threshold, window, hit count, time range and links to every evidence event. An alert means *suspicious behaviour that requires investigation* — never a confirmed attack (FR-13).

Definitions live in `backend/app/services/detection/rules.py` and are synced into the `detection_rules` table on start-up. The engine reads thresholds from the table, so you can tune or disable a rule in the database without a code change:

```sql
UPDATE detection_rules SET threshold = 8 WHERE rule_code = 'SSH_BRUTE_FORCE';
-- then "Re-run detection" on a dataset (or POST /api/v1/datasets/{id}/detect)
```

## Rule catalogue (v1)

| Rule | Source | Counts events where… | Threshold | Window | Severity |
|---|---|---|---|---|---|
| `SSH_BRUTE_FORCE` | SSH | `auth_result = FAILURE` (`Failed password …`, incl. *for invalid user*) | ≥ 5 | 300 s | HIGH |
| `HTTP_404_BURST` | NGINX | `status_code = 404` | ≥ 20 | 120 s | MEDIUM |
| `SENSITIVE_PATH_PROBE` | NGINX | normalised path is sensitive (below) | ≥ 10 | 120 s | MEDIUM |

`Invalid user …` lines (`INVALID_USER`) are **not** counted by `SSH_BRUTE_FORCE`, because OpenSSH logs both `Invalid user X` and `Failed password for invalid user X` for the same attempt — counting both would double-count.

**Sensitive paths:** `/admin`, `/administrator`, `/wp-admin`, `/wp-login.php`, `/xmlrpc.php`, `/phpmyadmin`, `/pma`, `/.env`, `/.git`, `/server-status`, `/actuator`, `/cgi-bin`. Paths are normalised first: query/fragment removed, percent-decoded (`/%61dmin` → `/admin`), lower-cased, duplicate and trailing slashes removed. A path matches if it equals an entry, is below it (`/admin/users`), or contains it as a segment (`/blog/wp-login.php`). `/administration-guide` and `/xadmin` do not match.

## Algorithm

For each rule and each source IP, events are sorted by `(timestamp, id)`:

1. Maintain a deque of matching events where `newest.ts − oldest.ts ≤ window` (**inclusive** boundary).
2. When the deque first reaches the threshold, an *episode* opens with the deque contents as evidence.
3. While open, every further matching event within `window` seconds of the episode's last event is appended — a sustained attack is one alert, not hundreds.
4. A gap longer than the window closes the episode; a later burst opens a new alert.

Events without a source IP are skipped and counted in `datasets.detection_skipped`. Events from different datasets are never combined (detection always runs per dataset).

## Idempotency (FR-12, NFR-11)

`dedup_key = "{dataset_id}:{rule_code}:{source_ip}:{first_evidence_event_id}"`. On re-run:

* existing key → alert updated in place (counts, evidence rebuilt), **status and notes preserved**;
* new key → alert inserted with status `OPEN`;
* key no longer produced (e.g. threshold raised) → alert removed.

## Test coverage (`backend/tests/test_detection.py`)

| Check (SRS §7.6) | Test |
|---|---|
| Positive / negative per rule | `test_exactly_threshold_triggers`, `test_one_below_threshold_does_not_trigger`, `test_triggers_at_20`, `test_19_does_not_trigger`, `test_triggers_at_10_and_not_9` |
| Window boundary inside / just outside | `test_window_boundary_inclusive` (300 s), `test_just_outside_window` (301 s) |
| No cross-dataset merging | `test_cross_dataset_events_not_merged` |
| Same IP, different rules → independent alerts | `test_independent_from_404_rule_for_same_ip` |
| Idempotent re-runs keep status & notes | `test_rerun_is_idempotent_and_preserves_status_and_notes` |
| Stale alerts removed | `test_stale_alerts_removed_when_rule_tightened` |

## Known false-positive scenarios

| Rule | Benign cause |
|---|---|
| `SSH_BRUTE_FORCE` | A user or script with a stale password retrying; a shared NAT/VPN egress IP with many users mistyping. |
| `HTTP_404_BURST` | A broken deployment (missing assets) or an SPA requesting removed routes; uptime/SEO crawlers. |
| `SENSITIVE_PATH_PROBE` | Real administrators using `/admin`; WordPress sites where `/wp-admin` is normal traffic. |

## Version history

| Version | Date | Change |
|---|---|---|
| 1 | 2026-11-10 | Initial rules per SRS §7.2. |

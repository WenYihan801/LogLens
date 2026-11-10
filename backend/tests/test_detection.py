"""Rule engine tests: positives, negatives, window boundaries, isolation, idempotency."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.database.models import AlertEvidence, AlertNote, Dataset, LogEvent, SecurityAlert
from app.services.detection.engine import EventView, RuleConfig, find_episodes, run_detection
from app.services.detection.rules import (
    HTTP_404_BURST,
    SENSITIVE_PATH_PROBE,
    SSH_BRUTE_FORCE,
    is_sensitive_path,
    normalise_path,
)

T0 = datetime(2026, 11, 3, 8, 0, tzinfo=timezone.utc)
SSH_RULE = RuleConfig(SSH_BRUTE_FORCE, "SSH", threshold=5, window_seconds=300)
HTTP_RULE = RuleConfig(HTTP_404_BURST, "NGINX", threshold=20, window_seconds=120)
PATH_RULE = RuleConfig(SENSITIVE_PATH_PROBE, "NGINX", threshold=10, window_seconds=120)


def ssh_fail(i, seconds, ip="203.0.113.1", result="FAILURE"):
    return EventView(i, T0 + timedelta(seconds=seconds), "SSH", ip, auth_result=result)


def http(i, seconds, status=404, path="/x", ip="203.0.113.2"):
    return EventView(i, T0 + timedelta(seconds=seconds), "NGINX", ip, status_code=status, request_path=path)


# ---------------------------------------------------------------- SSH_BRUTE_FORCE
class TestSSHBruteForce:
    def test_exactly_threshold_triggers(self):
        eps, _ = find_episodes([ssh_fail(i, i * 10) for i in range(5)], SSH_RULE)
        assert len(eps) == 1 and len(eps[0].events) == 5

    def test_one_below_threshold_does_not_trigger(self):
        eps, _ = find_episodes([ssh_fail(i, i * 10) for i in range(4)], SSH_RULE)
        assert eps == []

    def test_window_boundary_inclusive(self):
        # 5 events spanning exactly 300 s -> inside the window
        eps, _ = find_episodes([ssh_fail(i, i * 75) for i in range(5)], SSH_RULE)
        assert len(eps) == 1

    def test_just_outside_window(self):
        # 5 events spanning 301 s -> never 5 inside any 300 s window
        times = [0, 75, 150, 225, 301]
        eps, _ = find_episodes([ssh_fail(i, t) for i, t in enumerate(times)], SSH_RULE)
        assert eps == []

    def test_successes_and_invalid_user_lines_not_counted(self):
        evs = [ssh_fail(i, i, result="SUCCESS") for i in range(10)]
        evs += [ssh_fail(100 + i, i, result="INVALID_USER") for i in range(10)]
        assert find_episodes(evs, SSH_RULE)[0] == []

    def test_sustained_attack_is_one_alert(self):
        eps, _ = find_episodes([ssh_fail(i, i * 5) for i in range(100)], SSH_RULE)
        assert len(eps) == 1 and len(eps[0].events) == 100

    def test_two_bursts_separated_by_gap_are_two_alerts(self):
        evs = [ssh_fail(i, i * 5) for i in range(6)]
        evs += [ssh_fail(10 + i, 2000 + i * 5) for i in range(6)]
        eps, _ = find_episodes(evs, SSH_RULE)
        assert len(eps) == 2
        assert {e.id for e in eps[0].events}.isdisjoint({e.id for e in eps[1].events})

    def test_ips_are_independent(self):
        evs = [ssh_fail(i, i, ip="192.0.2.1") for i in range(3)]
        evs += [ssh_fail(10 + i, i, ip="192.0.2.2") for i in range(3)]
        assert find_episodes(evs, SSH_RULE)[0] == []

    def test_missing_ip_skipped_and_counted(self):
        evs = [ssh_fail(i, i, ip=None) for i in range(6)]
        eps, skipped = find_episodes(evs, SSH_RULE)
        assert eps == [] and skipped == 6

    def test_unsorted_input(self):
        evs = [ssh_fail(i, t) for i, t in enumerate([40, 0, 30, 10, 20])]
        eps, _ = find_episodes(evs, SSH_RULE)
        assert [e.id for e in eps[0].events] == [1, 3, 4, 2, 0]


# ---------------------------------------------------------------- HTTP rules
class TestHTTP404Burst:
    def test_triggers_at_20(self):
        eps, _ = find_episodes([http(i, i * 5) for i in range(20)], HTTP_RULE)
        assert len(eps) == 1

    def test_19_does_not_trigger(self):
        assert find_episodes([http(i, i * 5) for i in range(19)], HTTP_RULE)[0] == []

    def test_other_status_codes_ignored(self):
        evs = [http(i, i, status=200) for i in range(50)] + [http(100 + i, i, status=403) for i in range(50)]
        assert find_episodes(evs, HTTP_RULE)[0] == []

    def test_spread_out_404s_do_not_trigger(self):
        # 30 events at 10 s spacing -> 13 inside any 120 s window -> no alert
        assert find_episodes([http(i, i * 10) for i in range(30)], HTTP_RULE)[0] == []


class TestSensitivePathProbe:
    @pytest.mark.parametrize(
        "path",
        ["/admin", "/ADMIN/", "/admin/users?id=1", "/wp-login.php", "/blog/wp-login.php",
         "/phpmyadmin/index.php", "/.env", "//.git/config", "/%61dmin", "/server-status"],
    )
    def test_sensitive(self, path):
        assert is_sensitive_path(path)

    @pytest.mark.parametrize("path", ["/", "/administration-guide", "/blog/admins-are-people", "/login", None, "/xadmin"])
    def test_not_sensitive(self, path):
        assert not is_sensitive_path(path)

    def test_normalise_path(self):
        assert normalise_path("//Admin//Users/?x=1#frag") == "/admin/users"

    def test_triggers_at_10_and_not_9(self):
        assert len(find_episodes([http(i, i, 403, "/admin") for i in range(10)], PATH_RULE)[0]) == 1
        assert find_episodes([http(i, i, 403, "/admin") for i in range(9)], PATH_RULE)[0] == []

    def test_independent_from_404_rule_for_same_ip(self):
        evs = [http(i, i, 404, "/wp-login.php") for i in range(25)]
        a = find_episodes(evs, HTTP_RULE)[0]
        b = find_episodes(evs, PATH_RULE)[0]
        assert len(a) == 1 and len(b) == 1 and a[0].rule_code != b[0].rule_code


def test_source_type_mismatch_ignored():
    evs = [EventView(i, T0 + timedelta(seconds=i), "NGINX", "192.0.2.1", auth_result="FAILURE") for i in range(10)]
    assert find_episodes(evs, SSH_RULE)[0] == []


# ---------------------------------------------------------------- persistence / idempotency
def _make_dataset(db, n_fail=6, ip="203.0.113.50"):
    ds = Dataset(
        name="t", source_type="SSH", original_filename="t.log", file_sha256="0" * 64,
        size_bytes=1, total_lines=n_fail, parsed_lines=n_fail, failed_lines=0, status="COMPLETED",
    )
    db.add(ds)
    db.flush()
    for i in range(n_fail):
        db.add(
            LogEvent(
                dataset_id=ds.id, event_timestamp=T0 + timedelta(seconds=i * 10), source_type="SSH",
                source_ip=ip, auth_result="FAILURE", raw_message=f"line {i}", line_number=i + 1,
            )
        )
    db.commit()
    return ds


def test_rerun_is_idempotent_and_preserves_status_and_notes(db):
    ds = _make_dataset(db)
    r1 = run_detection(db, ds.id, "SSH")
    db.commit()
    assert (r1.alerts_total, r1.created) == (1, 1)
    alert = db.scalar(select(SecurityAlert))
    alert.status = "ACKNOWLEDGED"
    db.add(AlertNote(alert_id=alert.id, note="looking"))
    db.commit()

    for _ in range(3):
        r = run_detection(db, ds.id, "SSH")
        db.commit()
        assert (r.created, r.updated, r.removed) == (0, 1, 0)

    assert db.scalar(select(func.count()).select_from(SecurityAlert)) == 1
    assert db.scalar(select(func.count()).select_from(AlertEvidence)) == 6
    db.refresh(alert)
    assert alert.status == "ACKNOWLEDGED" and len(alert.notes) == 1


def test_stale_alerts_removed_when_rule_tightened(db):
    from app.database.models import DetectionRule

    ds = _make_dataset(db)
    run_detection(db, ds.id, "SSH")
    db.commit()
    rule = db.scalar(select(DetectionRule).where(DetectionRule.rule_code == SSH_BRUTE_FORCE))
    rule.threshold = 50
    db.commit()
    r = run_detection(db, ds.id, "SSH")
    db.commit()
    assert r.removed == 1 and db.scalar(select(func.count()).select_from(SecurityAlert)) == 0


def test_disabled_rule_does_not_run(db):
    from app.database.models import DetectionRule

    ds = _make_dataset(db)
    db.execute(DetectionRule.__table__.update().values(enabled=False))
    db.commit()
    assert run_detection(db, ds.id, "SSH").alerts_total == 0


def test_cross_dataset_events_not_merged(db):
    # 3 failures in each of two datasets from the same IP -> no alert anywhere
    a = _make_dataset(db, n_fail=3)
    b = _make_dataset(db, n_fail=3)
    assert run_detection(db, a.id, "SSH").alerts_total == 0
    assert run_detection(db, b.id, "SSH").alerts_total == 0


def test_dedup_key_scoped_to_dataset(db):
    a = _make_dataset(db)
    b = _make_dataset(db)
    run_detection(db, a.id, "SSH")
    run_detection(db, b.id, "SSH")
    db.commit()
    keys = list(db.scalars(select(SecurityAlert.dedup_key)))
    assert len(keys) == 2 and len(set(keys)) == 2
    assert all(isinstance(uuid.UUID(k.split(":")[0]), uuid.UUID) for k in keys)

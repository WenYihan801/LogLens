from datetime import datetime, timezone

import pytest

from app.services.normaliser import NormalisedEvent, ParseFailure, normalise_ip, preview
from app.services.parsers import nginx_parser, sniff_source_type
from app.services.parsers.ssh_parser import SSHParser

NGINX_OK = (
    '203.0.113.5 - - [03/Nov/2026:10:15:32 +0800] "GET /index.html?x=1 HTTP/1.1" 200 512 '
    '"https://example.com/" "Mozilla/5.0 (Macintosh)"'
)


# ---------------------------------------------------------------- nginx
class TestNginxParser:
    def test_combined_format(self):
        ev = nginx_parser.parse_line(NGINX_OK, 1)
        assert isinstance(ev, NormalisedEvent)
        assert ev.source_ip == "203.0.113.5"
        assert ev.http_method == "GET"
        assert ev.request_path == "/index.html?x=1"
        assert ev.status_code == 200
        assert ev.user_agent == "Mozilla/5.0 (Macintosh)"
        assert ev.source_type == "NGINX"
        assert ev.raw_message == NGINX_OK

    def test_timestamp_converted_to_utc(self):
        ev = nginx_parser.parse_line(NGINX_OK, 1)
        assert ev.event_timestamp == datetime(2026, 11, 3, 2, 15, 32, tzinfo=timezone.utc)

    def test_common_format_without_referer_and_ua(self):
        line = '192.0.2.1 - frank [03/Nov/2026:10:00:00 +0000] "POST /api HTTP/1.0" 201 12'
        ev = nginx_parser.parse_line(line, 7)
        assert isinstance(ev, NormalisedEvent)
        assert ev.http_method == "POST" and ev.status_code == 201
        assert ev.user_agent is None and ev.line_number == 7

    def test_ipv6(self):
        line = '2001:db8::1 - - [03/Nov/2026:10:00:00 +0000] "GET / HTTP/2.0" 404 0 "-" "curl/8"'
        ev = nginx_parser.parse_line(line, 1)
        assert ev.source_ip == "2001:db8::1" and ev.status_code == 404

    def test_ipv4_mapped_ipv6_is_normalised(self):
        assert normalise_ip("::ffff:192.0.2.9") == "192.0.2.9"

    def test_escaped_quotes_in_user_agent(self):
        line = '192.0.2.1 - - [03/Nov/2026:10:00:00 +0000] "GET / HTTP/1.1" 200 1 "-" "a \\"quoted\\" ua"'
        ev = nginx_parser.parse_line(line, 1)
        assert ev.user_agent == 'a "quoted" ua'

    def test_garbage_request_line_kept_without_method(self):
        line = '192.0.2.1 - - [03/Nov/2026:10:00:00 +0000] "\\x16\\x03\\x01" 400 157 "-" "-"'
        ev = nginx_parser.parse_line(line, 1)
        assert isinstance(ev, NormalisedEvent)
        assert ev.http_method is None and ev.request_path is None and ev.status_code == 400

    def test_very_long_user_agent_is_truncated(self):
        ua = "A" * 10_000
        line = f'192.0.2.1 - - [03/Nov/2026:10:00:00 +0000] "GET / HTTP/1.1" 200 1 "-" "{ua}"'
        ev = nginx_parser.parse_line(line, 1)
        assert len(ev.user_agent) == 2000
        assert ev.raw_message == line  # raw stays intact for review

    @pytest.mark.parametrize(
        "line,code",
        [
            ("totally not a log line", "NGINX_FORMAT_MISMATCH"),
            ("", "NGINX_FORMAT_MISMATCH"),
            ('192.0.2.1 - - [31/Foo/2026:10:00:00 +0000] "GET / HTTP/1.1" 200 1 "-" "-"', "INVALID_TIMESTAMP"),
            ('192.0.2.1 - - [03/Nov/2026:10:00:00] "GET / HTTP/1.1" 200 1 "-" "-"', "INVALID_TIMESTAMP"),
            ('999.1.1.1 - - [03/Nov/2026:10:00:00 +0000] "GET / HTTP/1.1" 200 1 "-" "-"', "INVALID_IP"),
            ('192.0.2.1 - - [03/Nov/2026:10:00:00 +0000] "GET / HTTP/1.1" 999 1 "-" "-"', "INVALID_STATUS_CODE"),
        ],
    )
    def test_failures(self, line, code):
        res = nginx_parser.parse_line(line, 3)
        assert isinstance(res, ParseFailure)
        assert res.error_code == code
        assert res.line_number == 3

    def test_preview_is_bounded(self):
        res = nginx_parser.parse_line("x" * 5000, 1)
        assert isinstance(res, ParseFailure)
        assert len(res.raw_preview) == 500
        assert len(preview("a\nb")) == 4  # newlines escaped, single-line


# ---------------------------------------------------------------- ssh
@pytest.fixture
def ssh():
    return SSHParser(year=2026, tz_name="UTC")


class TestSSHParser:
    def test_failed_password(self, ssh):
        ev = ssh.parse_line(
            "Nov  3 08:15:01 web-01 sshd[2211]: Failed password for root from 203.0.113.7 port 50122 ssh2", 1
        )
        assert isinstance(ev, NormalisedEvent)
        assert (ev.username, ev.source_ip, ev.auth_result) == ("root", "203.0.113.7", "FAILURE")
        assert ev.event_timestamp == datetime(2026, 11, 3, 8, 15, 1, tzinfo=timezone.utc)

    def test_failed_password_for_invalid_user(self, ssh):
        ev = ssh.parse_line(
            "Nov 13 08:15:01 h sshd[1]: Failed password for invalid user oracle from 203.0.113.7 port 1 ssh2", 1
        )
        assert ev.username == "oracle" and ev.auth_result == "FAILURE"

    def test_accepted_publickey(self, ssh):
        ev = ssh.parse_line(
            "2026-11-03T08:15:01.123456+00:00 web-01 sshd[2211]: Accepted publickey for alice from 192.0.2.4 port 5 ssh2: ED25519 SHA256:x",
            1,
        )
        assert (ev.username, ev.auth_result) == ("alice", "SUCCESS")
        assert ev.event_timestamp.microsecond == 123456

    def test_invalid_user(self, ssh):
        ev = ssh.parse_line("2026-11-03T08:15:01Z h sshd[9]: Invalid user admin from 203.0.113.9 port 4444", 1)
        assert (ev.username, ev.auth_result, ev.source_ip) == ("admin", "INVALID_USER", "203.0.113.9")

    def test_ipv6_source(self, ssh):
        ev = ssh.parse_line(
            "2026-11-03T08:15:01+00:00 h sshd[9]: Failed password for deploy from 2001:db8:bad::7 port 1 ssh2", 1
        )
        assert ev.source_ip == "2001:db8:bad::7"

    def test_iso_offset_converted_to_utc(self, ssh):
        ev = ssh.parse_line(
            "2026-11-03T16:00:00+08:00 h sshd[9]: Failed password for a from 192.0.2.1 port 1 ssh2", 1
        )
        assert ev.event_timestamp == datetime(2026, 11, 3, 8, 0, tzinfo=timezone.utc)

    def test_configured_timezone_for_classic_syslog(self):
        p = SSHParser(year=2026, tz_name="Asia/Singapore")
        ev = p.parse_line("Nov  3 16:00:00 h sshd[1]: Failed password for a from 192.0.2.1 port 1 ssh2", 1)
        assert ev.event_timestamp == datetime(2026, 11, 3, 8, 0, tzinfo=timezone.utc)

    @pytest.mark.parametrize(
        "line,code",
        [
            ("Nov  3 08:17:01 h CRON[5]: pam_unix(cron:session): session opened", "NOT_SSHD_LINE"),
            ("Nov  3 08:17:01 h sshd[5]: Received disconnect from 192.0.2.1 port 1:11: bye", "UNSUPPORTED_SSH_MESSAGE"),
            ("garbage", "SSH_FORMAT_MISMATCH"),
            ("Feb 30 08:17:01 h sshd[5]: Failed password for a from 192.0.2.1 port 1 ssh2", "INVALID_TIMESTAMP"),
            ("Nov  3 08:17:01 h sshd[5]: Failed password for a from 1.2.3 port 1 ssh2", "INVALID_IP"),
        ],
    )
    def test_failures(self, ssh, line, code):
        res = ssh.parse_line(line, 1)
        assert isinstance(res, ParseFailure) and res.error_code == code


def test_sniff_source_type():
    assert sniff_source_type([NGINX_OK]) == "NGINX"
    assert sniff_source_type(["Nov  3 08:15:01 h sshd[1]: Accepted password for a from 192.0.2.1 port 1 ssh2"]) == "SSH"
    assert sniff_source_type(["hello world"]) is None

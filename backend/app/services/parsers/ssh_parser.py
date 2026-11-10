"""SSH authentication log parser (FR-06).

Only the *agreed sample format* is guaranteed (see docs/log-formats.md). Two
timestamp styles are accepted:

* RFC 3339 / ISO 8601 (Ubuntu 24.04+ default rsyslog format)::

    2026-11-03T08:15:01.123456+00:00 web-01 sshd[2211]: Failed password for root from 203.0.113.7 port 50122 ssh2

* Classic BSD syslog (no year, no timezone)::

    Nov  3 08:15:01 web-01 sshd[2211]: Failed password for root from 203.0.113.7 port 50122 ssh2

  The year and timezone for classic lines come from configuration
  (``SSH_LOG_YEAR`` / ``SSH_LOG_TIMEZONE``) so the interpretation is explicit.

Recognised sshd messages:

* ``Failed password for [invalid user] <user> from <ip> port <n>``  -> FAILURE
* ``Accepted password|publickey|keyboard-interactive/pam for <user> from <ip>`` -> SUCCESS
* ``Invalid user <user> from <ip>``                                 -> INVALID_USER
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.services.normaliser import NormalisedEvent, ParseFailure, normalise_ip, preview, to_utc

SOURCE_TYPE = "SSH"

_ISO_PREFIX = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2}))\s+"
    r"(?P<host>\S+)\s+(?P<prog>[\w.\-/]+)(?:\[(?P<pid>\d+)\])?:\s?(?P<msg>.*)$"
)
_SYSLOG_PREFIX = re.compile(
    r"^(?P<ts>[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+"
    r"(?P<host>\S+)\s+(?P<prog>[\w.\-/]+)(?:\[(?P<pid>\d+)\])?:\s?(?P<msg>.*)$"
)

_IP = r"(?P<ip>[0-9A-Fa-f:.]+)"
_MSG_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(rf"^Failed (?:password|keyboard-interactive/pam) for (?:invalid user )?(?P<user>\S*) from {_IP} port \d+"),
        "FAILURE",
    ),
    (
        re.compile(rf"^Accepted (?:password|publickey|keyboard-interactive/pam) for (?P<user>\S+) from {_IP} port \d+"),
        "SUCCESS",
    ),
    (re.compile(rf"^Invalid user (?P<user>\S*) from {_IP}(?: port \d+)?"), "INVALID_USER"),
]


def _parse_iso(ts: str) -> datetime:
    ts = ts.replace(" ", "T", 1).replace("Z", "+00:00")
    return datetime.fromisoformat(ts)


def _parse_syslog(ts: str, year: int, tz: ZoneInfo) -> datetime:
    collapsed = re.sub(r"\s+", " ", ts)
    naive = datetime.strptime(f"{year} {collapsed}", "%Y %b %d %H:%M:%S")
    return naive.replace(tzinfo=tz)


def _split_prefix(raw: str, year: int, tz: ZoneInfo):
    m = _ISO_PREFIX.match(raw)
    if m:
        return m, _parse_iso(m.group("ts"))
    m = _SYSLOG_PREFIX.match(raw)
    if m:
        return m, _parse_syslog(m.group("ts"), year, tz)
    return None, None


def looks_like_ssh(line: str) -> bool:
    raw = line.strip()
    return bool((_ISO_PREFIX.match(raw) or _SYSLOG_PREFIX.match(raw)) and "sshd" in raw)


class SSHParser:
    def __init__(self, year: int = 0, tz_name: str = "UTC") -> None:
        self.year = year or datetime.now(timezone.utc).year
        self.tz = ZoneInfo(tz_name)

    def parse_line(self, line: str, line_number: int) -> NormalisedEvent | ParseFailure:
        raw = line.rstrip("\r\n")
        try:
            m, ts = _split_prefix(raw.strip(), self.year, self.tz)
        except ValueError:
            return ParseFailure(
                line_number,
                "INVALID_TIMESTAMP",
                "Timestamp could not be parsed. Expected ISO 8601 or 'Mon dd HH:MM:SS'.",
                preview(raw),
            )
        if m is None:
            return ParseFailure(
                line_number,
                "SSH_FORMAT_MISMATCH",
                "Line does not match the supported syslog/auth.log prefix (timestamp host program[pid]: message).",
                preview(raw),
            )
        if not m.group("prog").endswith("sshd"):
            return ParseFailure(
                line_number,
                "NOT_SSHD_LINE",
                f"Line comes from '{m.group('prog')[:40]}', not sshd; only sshd authentication events are imported.",
                preview(raw),
            )

        msg = m.group("msg")
        for pattern, result in _MSG_PATTERNS:
            mm = pattern.match(msg)
            if not mm:
                continue
            try:
                ip = normalise_ip(mm.group("ip"))
            except ValueError:
                return ParseFailure(
                    line_number,
                    "INVALID_IP",
                    f"Source address '{mm.group('ip')[:45]}' is not a valid IP address.",
                    preview(raw),
                )
            return NormalisedEvent(
                event_timestamp=to_utc(ts),
                source_type=SOURCE_TYPE,
                raw_message=raw,
                line_number=line_number,
                source_ip=ip,
                username=(mm.group("user") or None),
                auth_result=result,
            )

        return ParseFailure(
            line_number,
            "UNSUPPORTED_SSH_MESSAGE",
            "sshd message type is not supported in V1.0 (only Failed/Accepted password and Invalid user).",
            preview(raw),
        )

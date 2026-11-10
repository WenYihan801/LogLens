"""Unified event structure shared by all parsers (FR-07).

Parsers return either a ``NormalisedEvent`` or a ``ParseFailure`` per line, never
raise for bad input, so one malformed line cannot abort an import (FR-08 / NFR-10).
"""

from __future__ import annotations

import ipaddress
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

RAW_PREVIEW_LIMIT = 500
MAX_USER_AGENT = 2000
MAX_PATH = 4000


@dataclass(slots=True)
class NormalisedEvent:
    event_timestamp: datetime  # always tz-aware UTC
    source_type: str
    raw_message: str
    line_number: int
    source_ip: str | None = None
    http_method: str | None = None
    request_path: str | None = None
    status_code: int | None = None
    user_agent: str | None = None
    username: str | None = None
    auth_result: str | None = None

    def as_row(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class ParseFailure:
    line_number: int
    error_code: str
    error_message: str
    raw_preview: str


def preview(raw: str, limit: int = RAW_PREVIEW_LIMIT) -> str:
    """Return a bounded-length, single-line preview of untrusted input."""
    cleaned = raw.replace("\r", "\\r").replace("\n", "\\n")
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 3] + "..."


def to_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware before normalisation")
    return ts.astimezone(timezone.utc)


def normalise_ip(value: str | None) -> str | None:
    """Validate and canonicalise IPv4/IPv6 text. Returns None for '-' or empty.

    Raises ValueError for anything that is not an IP address.
    """
    if value is None:
        return None
    value = value.strip()
    if value in ("", "-"):
        return None
    # Strip IPv6 zone / brackets occasionally seen in logs
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    ip = ipaddress.ip_address(value)
    # Represent IPv4-mapped IPv6 (::ffff:1.2.3.4) as plain IPv4 so rules group correctly.
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return str(ip)


def truncate(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    return value if len(value) <= limit else value[:limit]

"""Nginx access log parser (FR-05).

Supports the default ``combined`` format and the shorter ``common`` format:

    $remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent"
"""

from __future__ import annotations

import re
from datetime import datetime

from app.services.normaliser import (
    MAX_PATH,
    MAX_USER_AGENT,
    NormalisedEvent,
    ParseFailure,
    normalise_ip,
    preview,
    to_utc,
    truncate,
)

SOURCE_TYPE = "NGINX"

# A quoted field where \" and \\ escapes are allowed inside.
_Q = r'(?:[^"\\]|\\.)*'
_LINE_RE = re.compile(
    r"^(?P<ip>\S+)\s+\S+\s+(?P<user>\S+)\s+"
    r"\[(?P<time>[^\]]+)\]\s+"
    rf'"(?P<request>{_Q})"\s+'
    r"(?P<status>\d{3})\s+(?P<size>\S+)"
    rf'(?:\s+"(?P<referer>{_Q})"\s+"(?P<ua>{_Q})")?'
    r"(?:\s.*)?$"
)
_TIME_FMT = "%d/%b/%Y:%H:%M:%S %z"
_METHOD_RE = re.compile(r"^[A-Z]{3,10}$")


def _unescape(value: str | None) -> str | None:
    if value is None:
        return None
    # Nginx escapes " and non-printables as \xHH; we only undo \" and \\ for readability.
    return value.replace('\\"', '"').replace("\\\\", "\\")


def looks_like_nginx(line: str) -> bool:
    return bool(_LINE_RE.match(line.strip()))


def parse_line(line: str, line_number: int) -> NormalisedEvent | ParseFailure:
    raw = line.rstrip("\r\n")
    m = _LINE_RE.match(raw.strip())
    if not m:
        return ParseFailure(
            line_number,
            "NGINX_FORMAT_MISMATCH",
            "Line does not match the Nginx combined/common access log format.",
            preview(raw),
        )

    try:
        ts = to_utc(datetime.strptime(m.group("time"), _TIME_FMT))
    except ValueError:
        return ParseFailure(
            line_number,
            "INVALID_TIMESTAMP",
            f"Timestamp '{m.group('time')[:40]}' is not in the expected format dd/Mon/yyyy:HH:MM:SS +zzzz.",
            preview(raw),
        )

    try:
        ip = normalise_ip(m.group("ip"))
    except ValueError:
        return ParseFailure(
            line_number,
            "INVALID_IP",
            f"Source address '{m.group('ip')[:45]}' is not a valid IPv4 or IPv6 address.",
            preview(raw),
        )

    status = int(m.group("status"))
    if not 100 <= status <= 599:
        return ParseFailure(
            line_number,
            "INVALID_STATUS_CODE",
            f"HTTP status {status} is outside the valid range 100-599.",
            preview(raw),
        )

    method: str | None = None
    path: str | None = None
    request = _unescape(m.group("request")) or ""
    parts = request.split(" ")
    if len(parts) >= 2 and _METHOD_RE.match(parts[0]):
        method = parts[0]
        # Path may itself contain spaces in malformed requests; drop trailing protocol.
        if len(parts) >= 3 and parts[-1].upper().startswith("HTTP/"):
            path = " ".join(parts[1:-1])
        else:
            path = " ".join(parts[1:])
    elif request and request != "-":
        # Garbage request line (e.g. TLS handshake bytes sent to an HTTP port).
        # Keep the event (status code is still meaningful) but no method/path.
        path = None

    ua = _unescape(m.group("ua"))
    if ua == "-":
        ua = None

    return NormalisedEvent(
        event_timestamp=ts,
        source_type=SOURCE_TYPE,
        raw_message=raw,
        line_number=line_number,
        source_ip=ip,
        http_method=method,
        request_path=truncate(path, MAX_PATH),
        status_code=status,
        user_agent=truncate(ua, MAX_USER_AGENT),
    )

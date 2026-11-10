"""Upload validation (FR-02, NFR-04). Content is only read as text — never executed."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass

from app.core.errors import AppError
from app.services.parsers import format_match_count, sniff_source_type

ALLOWED_EXTENSIONS = {".log", ".txt"}
SNIFF_LINES = 50
# At least this share of sampled lines must look like the chosen format.
MIN_FORMAT_MATCH_RATIO = 0.2


@dataclass(slots=True)
class ValidatedFile:
    filename: str
    source_type: str
    lines: list[str]
    size_bytes: int
    sha256: str


def _safe_name(name: str | None) -> str:
    base = os.path.basename((name or "").replace("\\", "/")).strip()
    return base[:255] or "upload.log"


def _looks_binary(data: bytes) -> bool:
    head = data[:8192]
    if b"\x00" in head:
        return True
    # Control characters other than \t \n \r \f \v and ESC are rare in text logs.
    bad = sum(1 for b in head if b < 32 and b not in (9, 10, 11, 12, 13, 27))
    return len(head) > 0 and bad / len(head) > 0.05


def validate_upload(
    *,
    filename: str | None,
    data: bytes,
    requested_source: str | None,
    max_bytes: int,
    max_lines: int,
) -> ValidatedFile:
    name = _safe_name(filename)
    ext = os.path.splitext(name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise AppError(
            400,
            "UNSUPPORTED_FILE_TYPE",
            f"Files with extension '{ext or '(none)'}' are not supported. Upload a .log or .txt file.",
        )
    if len(data) == 0:
        raise AppError(400, "EMPTY_FILE", "The uploaded file is empty. Choose a file that contains log lines.")
    if len(data) > max_bytes:
        raise AppError(
            413,
            "FILE_TOO_LARGE",
            f"The file is {len(data) / 1024 / 1024:.1f} MB; the limit is {max_bytes / 1024 / 1024:.0f} MB. "
            "Split the log into smaller files and upload them separately.",
            {"size_bytes": len(data), "max_bytes": max_bytes},
        )
    if _looks_binary(data):
        raise AppError(
            400,
            "BINARY_FILE",
            "The file appears to be binary (e.g. compressed or an executable). "
            "Decompress .gz logs first and upload the plain-text file.",
        )
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AppError(
            400,
            "INVALID_ENCODING",
            "The file is not valid UTF-8 text. Re-save it as UTF-8 and try again.",
            {"byte_offset": exc.start},
        ) from None

    lines = text.splitlines()
    if len(lines) > max_lines:
        raise AppError(
            413,
            "TOO_MANY_LINES",
            f"The file has {len(lines):,} lines; the limit is {max_lines:,}. Split it into smaller files.",
            {"lines": len(lines), "max_lines": max_lines},
        )

    sample = [ln for ln in lines if ln.strip()][:SNIFF_LINES]
    if not sample:
        raise AppError(400, "EMPTY_FILE", "The file only contains blank lines.")

    source = (requested_source or "AUTO").upper()
    if source == "AUTO":
        guessed = sniff_source_type(sample)
        if guessed is None:
            raise AppError(
                422,
                "UNRECOGNISED_FORMAT",
                "Could not recognise the log format. Supported formats are Nginx access logs "
                "and the documented SSH auth.log format.",
            )
        source = guessed
    elif source not in ("NGINX", "SSH"):
        raise AppError(422, "INVALID_SOURCE_TYPE", "source_type must be NGINX, SSH or AUTO.")

    matched = format_match_count(source, sample)
    if matched / len(sample) < MIN_FORMAT_MATCH_RATIO:
        other = sniff_source_type(sample)
        hint = f" It looks more like a {other} log." if other and other != source else ""
        raise AppError(
            422,
            "FORMAT_MISMATCH",
            f"Only {matched} of the first {len(sample)} lines look like {source} log entries.{hint} "
            "Check the selected log type.",
            {"matched": matched, "sampled": len(sample), "suggested_source_type": other},
        )

    return ValidatedFile(
        filename=name,
        source_type=source,
        lines=lines,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )

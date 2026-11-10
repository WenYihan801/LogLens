"""Parser registry: one place that maps a source type to its line parser."""

from collections.abc import Callable

from app.core.config import get_settings
from app.services.normaliser import NormalisedEvent, ParseFailure
from app.services.parsers import nginx_parser, ssh_parser

LineParser = Callable[[str, int], NormalisedEvent | ParseFailure]


def get_parser(source_type: str) -> LineParser:
    if source_type == "NGINX":
        return nginx_parser.parse_line
    if source_type == "SSH":
        s = get_settings()
        return ssh_parser.SSHParser(year=s.ssh_log_year, tz_name=s.ssh_log_timezone).parse_line
    raise ValueError(f"Unsupported source type: {source_type}")


def sniff_source_type(lines: list[str]) -> str | None:
    """Guess the source type from a sample of non-empty lines (majority vote)."""
    nginx = sum(1 for ln in lines if nginx_parser.looks_like_nginx(ln))
    ssh = sum(1 for ln in lines if ssh_parser.looks_like_ssh(ln))
    if nginx == 0 and ssh == 0:
        return None
    return "NGINX" if nginx >= ssh else "SSH"


def format_match_count(source_type: str, lines: list[str]) -> int:
    check = nginx_parser.looks_like_nginx if source_type == "NGINX" else ssh_parser.looks_like_ssh
    return sum(1 for ln in lines if check(ln))

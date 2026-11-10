"""Detection rule definitions (FR-09, BR-10).

Thresholds, windows and severities live here — not in API routes. On startup they
are synced into the ``detection_rules`` table, which is what the engine reads, so a
rule can be disabled or tuned in the database without touching code.

Bump ``version`` whenever the logic or defaults of a rule change; the value is
shown in the UI and docs/detection-rules.md records the history.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import unquote

SSH_BRUTE_FORCE = "SSH_BRUTE_FORCE"
HTTP_404_BURST = "HTTP_404_BURST"
SENSITIVE_PATH_PROBE = "SENSITIVE_PATH_PROBE"

# Paths commonly targeted by automated scanners. Legitimate sites may use these
# too, which is why a hit only means "worth investigating".
SENSITIVE_PATHS: tuple[str, ...] = (
    "/admin",
    "/administrator",
    "/wp-admin",
    "/wp-login.php",
    "/xmlrpc.php",
    "/phpmyadmin",
    "/pma",
    "/.env",
    "/.git",
    "/server-status",
    "/actuator",
    "/cgi-bin",
)


@dataclass(frozen=True, slots=True)
class RuleDefinition:
    rule_code: str
    name: str
    description: str
    source_type: str
    threshold: int
    window_seconds: int
    severity: str
    version: int = 1


DEFAULT_RULES: tuple[RuleDefinition, ...] = (
    RuleDefinition(
        rule_code=SSH_BRUTE_FORCE,
        name="Possible SSH Brute Force",
        description=(
            "The same source IP produced at least {threshold} failed SSH password "
            "authentications within {window} seconds. Review the source IP, targeted "
            "accounts and any subsequent successful logins."
        ),
        source_type="SSH",
        threshold=5,
        window_seconds=300,
        severity="HIGH",
    ),
    RuleDefinition(
        rule_code=HTTP_404_BURST,
        name="HTTP 404 Burst",
        description=(
            "The same source IP received at least {threshold} HTTP 404 responses within "
            "{window} seconds. This pattern often indicates content discovery or a "
            "misconfigured client."
        ),
        source_type="NGINX",
        threshold=20,
        window_seconds=120,
        severity="MEDIUM",
    ),
    RuleDefinition(
        rule_code=SENSITIVE_PATH_PROBE,
        name="Sensitive Path Probing",
        description=(
            "The same source IP requested common administrative or login paths at least "
            "{threshold} times within {window} seconds. Legitimate administrators may "
            "trigger this; verify whether the source is expected."
        ),
        source_type="NGINX",
        threshold=10,
        window_seconds=120,
        severity="MEDIUM",
    ),
)


def normalise_path(path: str | None) -> str | None:
    """Canonical form for path matching: decoded, no query/fragment, lower-case,
    single slashes, no trailing slash."""
    if not path:
        return None
    p = path.split("?", 1)[0].split("#", 1)[0]
    p = unquote(p)  # never raises; invalid escapes are left as-is
    p = p.lower()
    while "//" in p:
        p = p.replace("//", "/")
    if len(p) > 1:
        p = p.rstrip("/")
    return p or "/"


def is_sensitive_path(path: str | None, sensitive: tuple[str, ...] = SENSITIVE_PATHS) -> bool:
    p = normalise_path(path)
    if p is None:
        return False
    # Match the path itself, anything beneath it, or the same path under a sub-dir
    # (e.g. /blog/wp-login.php, /backup/.env).
    for s in sensitive:
        if p == s or p.startswith(s + "/") or p.endswith(s) or (s + "/") in p:
            return True
    return False

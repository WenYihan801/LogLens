#!/usr/bin/env python3
"""Generate the synthetic sample logs in sample_data/ (deterministic, seed=42).

All IP addresses come from documentation ranges (RFC 5737: 192.0.2.0/24,
198.51.100.0/24, 203.0.113.0/24 and RFC 3849: 2001:db8::/32), so the data can
never point at a real host. Usernames and hostnames are invented.

    python3 scripts/generate_sample_data.py
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "sample_data"
rng = random.Random(42)
BASE = datetime(2026, 11, 3, 8, 0, 0, tzinfo=timezone.utc)

NORMAL_IPS = [f"192.0.2.{i}" for i in range(10, 60)] + [
    "2001:db8:85a3::8a2e:370:7334",
    "2001:db8::42",
]
UAS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
    "curl/8.7.1",
]
PAGES = [
    ("/", 200), ("/index.html", 200), ("/about", 200), ("/blog", 200),
    ("/blog/how-we-ship", 200), ("/blog/postgres-tips", 200), ("/pricing", 200),
    ("/contact", 200), ("/static/css/app.css", 200), ("/static/js/app.js", 200),
    ("/static/img/logo.svg", 200), ("/api/v1/products?page=2", 200),
    ("/api/v1/cart", 201), ("/favicon.ico", 200), ("/static/js/app.js", 304),
    ("/login", 200), ("/robots.txt", 200),
]


def nginx_line(ts: datetime, ip: str, method: str, path: str, status: int, ua: str, ref: str = "-") -> str:
    size = 0 if status in (204, 304) else rng.randint(180, 48000)
    t = ts.strftime("%d/%b/%Y:%H:%M:%S +0000")
    return f'{ip} - - [{t}] "{method} {path} HTTP/1.1" {status} {size} "{ref}" "{ua}"'


def normal_traffic(n: int, start: datetime, hours: float) -> list[tuple[datetime, str]]:
    out = []
    for _ in range(n):
        ts = start + timedelta(seconds=rng.uniform(0, hours * 3600))
        ip = rng.choice(NORMAL_IPS)
        path, status = rng.choice(PAGES)
        method = "POST" if path == "/api/v1/cart" else "GET"
        if rng.random() < 0.02:  # the occasional broken link
            path, status = rng.choice(["/blog/old-post", "/img/missing.png", "/docs/v0"]), 404
        out.append((ts, nginx_line(ts, ip, method, path, status, rng.choice(UAS), "https://example.com/")))
    return out


def write(path: Path, rows: list[tuple[datetime, str]]) -> None:
    rows.sort(key=lambda r: r[0])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(r[1] for r in rows) + "\n", encoding="utf-8")
    print(f"wrote {path.relative_to(ROOT.parent)} ({len(rows)} lines)")


def gen_nginx() -> None:
    write(ROOT / "nginx" / "normal_access.log", normal_traffic(800, BASE, 6))

    rows = normal_traffic(900, BASE, 6)
    scanner_ua = "Mozilla/5.0 (compatible; ExampleScanner/2.1; +https://scanner.example)"

    # HTTP_404_BURST: 203.0.113.45 – 36 x 404 within ~95 s
    t = BASE + timedelta(hours=2, minutes=14)
    for i in range(36):
        t += timedelta(seconds=rng.uniform(1.5, 3.0))
        p = rng.choice(["/backup.zip", "/old/", "/test.php", "/api/v0/users", "/config.bak",
                        "/shell.php", "/.svn/entries", "/upload/", "/tmp/", "/db.sql"])
        rows.append((t, nginx_line(t, "203.0.113.45", "GET", f"{p}?r={i}", 404, scanner_ua)))

    # SENSITIVE_PATH_PROBE: 198.51.100.23 – 14 hits within ~100 s
    t = BASE + timedelta(hours=4, minutes=2)
    probes = ["/wp-login.php", "/wp-admin/", "/phpmyadmin/", "/admin", "/admin/login",
              "/.env", "/.git/config", "/xmlrpc.php", "/PhpMyAdmin/index.php", "/administrator/",
              "/blog/wp-login.php", "/server-status", "/%61dmin", "/wp-admin/install.php"]
    for p in probes:
        t += timedelta(seconds=rng.uniform(4, 8))
        status = rng.choice([403, 404, 404, 401])
        rows.append((t, nginx_line(t, "198.51.100.23", rng.choice(["GET", "POST"]), p, status, "python-requests/2.32.3")))

    # Below-threshold negative: 198.51.100.88 – 6 sensitive hits spread out (no alert)
    t = BASE + timedelta(hours=1)
    for p in ["/admin", "/admin/users", "/admin", "/admin/settings", "/admin", "/admin/logs"]:
        t += timedelta(minutes=7)
        rows.append((t, nginx_line(t, "198.51.100.88", "GET", p, 200, UAS[0])))

    # Malformed / edge lines (demonstrate FR-08 error handling)
    t = BASE + timedelta(hours=3)
    rows.append((t, '192.0.2.77 - - [03/Nov/2026:11:00:00 +0000] "\\x16\\x03\\x01\\x02\\x00\\x01" 400 157 "-" "-"'))
    rows.append((t, '192.0.2.78 - - [31/Foo/2026:11:00:01 +0000] "GET / HTTP/1.1" 200 512 "-" "curl/8.7.1"'))
    rows.append((t, 'not-an-ip - - [03/Nov/2026:11:00:02 +0000] "GET / HTTP/1.1" 200 512 "-" "curl/8.7.1"'))
    rows.append((t, "this line is not an access log entry at all"))
    rows.append((t, '192.0.2.79 - - [03/Nov/2026:11:00:03 +0000] "GET /search?q==HYPERLINK(\\"http://x\\") HTTP/1.1" 200 99 "-" "=cmd|\' /C calc\'!A0"'))
    write(ROOT / "nginx" / "suspicious_access.log", rows)


def iso(ts: datetime) -> str:
    return ts.isoformat(timespec="microseconds")


def classic(ts: datetime) -> str:
    return ts.strftime("%b ") + f"{ts.day:>2}" + ts.strftime(" %H:%M:%S")


USERS = ["alice", "bob", "deploy", "carol", "backup"]


def gen_ssh() -> None:
    # Normal: classic syslog timestamps (year/timezone supplied by config).
    rows = []
    pid = 4000
    for _ in range(160):
        ts = BASE + timedelta(seconds=rng.uniform(0, 10 * 3600))
        ip = rng.choice(NORMAL_IPS[:15])
        user = rng.choice(USERS)
        pid += rng.randint(1, 9)
        method = rng.choice(["publickey", "publickey", "password"])
        if rng.random() < 0.08:  # a typo, then success a few seconds later
            rows.append((ts, f"{classic(ts)} bastion-01 sshd[{pid}]: Failed password for {user} from {ip} port {rng.randint(40000, 65000)} ssh2"))
            ts += timedelta(seconds=rng.randint(4, 12))
            method = "password"
        rows.append((ts, f"{classic(ts)} bastion-01 sshd[{pid}]: Accepted {method} for {user} from {ip} port {rng.randint(40000, 65000)} ssh2"))
    for h in range(0, 10, 3):
        ts = BASE + timedelta(hours=h, minutes=17)
        rows.append((ts, f"{classic(ts)} bastion-01 CRON[{pid + h}]: pam_unix(cron:session): session opened for user root(uid=0) by root(uid=0)"))
    ts = BASE + timedelta(hours=5, minutes=3)
    rows.append((ts, f"{classic(ts)} bastion-01 sshd[{pid + 50}]: Received disconnect from 192.0.2.12 port 51122:11: disconnected by user"))
    write(ROOT / "ssh" / "normal_auth.log", rows)

    # Brute force: ISO 8601 timestamps (Ubuntu 24.04 style).
    rows = []
    pid = 9000
    for _ in range(60):
        ts = BASE + timedelta(seconds=rng.uniform(0, 8 * 3600))
        user, ip = rng.choice(USERS), rng.choice(NORMAL_IPS[:10])
        pid += 3
        rows.append((ts, f"{iso(ts)} web-01 sshd[{pid}]: Accepted publickey for {user} from {ip} port {rng.randint(40000, 65000)} ssh2"))

    # 203.0.113.99 – rapid dictionary attack (~40 failures in ~3 min)
    t = BASE + timedelta(hours=1, minutes=30)
    for i in range(40):
        t += timedelta(seconds=rng.uniform(2, 6))
        pid += 1
        user = rng.choice(["root", "admin", "test", "oracle", "ubuntu", "pi", "postgres", "guest"])
        port = rng.randint(30000, 65000)
        if user in ("root", "ubuntu"):
            rows.append((t, f"{iso(t)} web-01 sshd[{pid}]: Failed password for {user} from 203.0.113.99 port {port} ssh2"))
        else:
            rows.append((t, f"{iso(t)} web-01 sshd[{pid}]: Invalid user {user} from 203.0.113.99 port {port}"))
            rows.append((t + timedelta(milliseconds=800), f"{iso(t + timedelta(milliseconds=800))} web-01 sshd[{pid}]: Failed password for invalid user {user} from 203.0.113.99 port {port} ssh2"))

    # 2001:db8:bad::7 – 7 failures in 90 s, then a success (worth a close look)
    t = BASE + timedelta(hours=5, minutes=10)
    for _ in range(7):
        t += timedelta(seconds=rng.uniform(8, 14))
        pid += 1
        rows.append((t, f"{iso(t)} web-01 sshd[{pid}]: Failed password for deploy from 2001:db8:bad::7 port {rng.randint(30000, 65000)} ssh2"))
    t += timedelta(seconds=20)
    rows.append((t, f"{iso(t)} web-01 sshd[{pid + 1}]: Accepted password for deploy from 2001:db8:bad::7 port 41022 ssh2"))

    # Negative case: 198.51.100.77 – 4 failures every 5 minutes (never 5 within 300 s)
    t = BASE + timedelta(hours=6)
    for burst in range(3):
        for _ in range(4):
            t += timedelta(seconds=20)
            pid += 1
            rows.append((t, f"{iso(t)} web-01 sshd[{pid}]: Failed password for backup from 198.51.100.77 port {rng.randint(30000, 65000)} ssh2"))
        t += timedelta(seconds=330)

    t = BASE + timedelta(hours=7)
    rows.append((t, f"{iso(t)} web-01 sshd[{pid + 9}]: Connection closed by authenticating user root 192.0.2.250 port 2222 [preauth]"))
    rows.append((t, f"{iso(t)} web-01 systemd[1]: Started session-42.scope - Session 42 of User alice."))
    write(ROOT / "ssh" / "brute_force_sample.log", rows)


if __name__ == "__main__":
    gen_nginx()
    gen_ssh()

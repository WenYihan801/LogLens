# Supported log formats

## Nginx access log

The default `combined` format and the shorter `common` format:

```nginx
log_format combined '$remote_addr - $remote_user [$time_local] '
                    '"$request" $status $body_bytes_sent '
                    '"$http_referer" "$http_user_agent"';
```

```
203.0.113.45 - - [03/Nov/2026:10:14:03 +0000] "GET /backup.zip HTTP/1.1" 404 512 "-" "ExampleScanner/2.1"
192.0.2.1 - frank [03/Nov/2026:10:00:00 +0000] "POST /api HTTP/1.0" 201 12
```

* Extracted: time (converted to UTC using the logged offset), source IP (IPv4/IPv6; `::ffff:a.b.c.d` normalised to IPv4), method, path, status, user agent, raw line.
* Escaped quotes (`\"`) inside quoted fields are supported.
* A garbage request line (e.g. TLS bytes sent to port 80, logged as status 400) is kept as an event with no method/path.
* User-Agent is truncated to 2,000 chars and path to 4,000 chars in the normalised fields; `raw_message` keeps the full line.

## SSH authentication log (agreed sample format)

Two timestamp styles are accepted:

```
# RFC 3339 / ISO 8601 – default on Ubuntu 24.04+ (rsyslog)
2026-11-03T09:30:05.319577+00:00 web-01 sshd[9181]: Invalid user admin from 203.0.113.99 port 51855

# Classic BSD syslog – no year, no timezone
Nov  3 08:16:49 bastion-01 sshd[4254]: Failed password for bob from 192.0.2.14 port 59566 ssh2
```

For the classic style the interpretation is configured explicitly:

| Variable | Default | Meaning |
|---|---|---|
| `SSH_LOG_YEAR` | `0` | Year to assume; `0` = current UTC year |
| `SSH_LOG_TIMEZONE` | `UTC` | IANA timezone of the server that wrote the log |

| sshd message | `auth_result` |
|---|---|
| `Failed password for [invalid user] <user> from <ip> port <n> …` | `FAILURE` |
| `Failed keyboard-interactive/pam for …` | `FAILURE` |
| `Accepted password\|publickey\|keyboard-interactive/pam for <user> from <ip> port <n> …` | `SUCCESS` |
| `Invalid user <user> from <ip> [port <n>]` | `INVALID_USER` |

Other sshd messages are recorded as `UNSUPPORTED_SSH_MESSAGE` and lines from other programs (CRON, systemd, sudo…) as `NOT_SSHD_LINE` — they appear in the dataset's import errors but never abort the import. This is a deliberate V1.0 scope limit (SRS §3.6).

## Synthetic sample data

`sample_data/` is generated deterministically by `scripts/generate_sample_data.py` (seed 42). All addresses come from documentation ranges (RFC 5737 `192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`; RFC 3849 `2001:db8::/32`), so no real host is referenced.

| File | Lines | Expected result |
|---|---|---|
| `nginx/normal_access.log` | 800 | 0 alerts (Dataset A) |
| `nginx/suspicious_access.log` | 961 | `HTTP_404_BURST` for 203.0.113.45, `SENSITIVE_PATH_PROBE` for 198.51.100.23, 198.51.100.88 below threshold, 3 malformed lines, a CSV-injection payload (Datasets C/D) |
| `ssh/normal_auth.log` | 177 | 0 alerts; CRON/disconnect lines show up as import errors (Dataset A) |
| `ssh/brute_force_sample.log` | 149 | `SSH_BRUTE_FORCE` for 203.0.113.99 and 2001:db8:bad::7; 198.51.100.77 stays below threshold (Dataset B) |

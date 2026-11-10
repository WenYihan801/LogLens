"""Tiny in-memory fixed-window rate limiter (NFR-09).

Good enough for a single-process deployment. For multiple workers or instances,
replace with a shared store (e.g. Redis) — noted as future work.
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.errors import AppError


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        if self.limit <= 0:
            return
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                retry = int(self.window - (now - hits[0])) + 1
                raise AppError(
                    429,
                    "RATE_LIMITED",
                    f"Too many uploads. Please wait about {retry} seconds and try again.",
                    {"retry_after_seconds": retry},
                )
            hits.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"

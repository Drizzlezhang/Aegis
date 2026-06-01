"""In-memory sliding-window rate limiter."""

from __future__ import annotations

import time
from collections import defaultdict


class RateLimiter:
    """Simple in-memory sliding-window rate limiter keyed by arbitrary string.

    Tracks per-minute and per-hour windows independently.
    """

    def __init__(self, per_minute: int = 10, per_hour: int = 60) -> None:
        self._per_minute = per_minute
        self._per_hour = per_hour
        self._minute_buckets: dict[str, list[float]] = defaultdict(list)
        self._hour_buckets: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> bool:
        """Check if an event for *key* is allowed. Returns True if allowed."""
        now = time.monotonic()

        # --- minute window ---
        minute_window = self._minute_buckets[key]
        # drop expired
        cutoff = now - 60
        minute_window[:] = [t for t in minute_window if t > cutoff]
        if len(minute_window) >= self._per_minute:
            return False
        minute_window.append(now)

        # --- hour window ---
        hour_window = self._hour_buckets[key]
        cutoff_h = now - 3600
        hour_window[:] = [t for t in hour_window if t > cutoff_h]
        if len(hour_window) >= self._per_hour:
            # roll back minute window append
            minute_window.pop()
            return False
        hour_window.append(now)

        return True

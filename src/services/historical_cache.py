"""SQLite-based historical OHLCV cache with TTL layering and LRU eviction."""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# TTL in seconds per interval category
TTL_MAP: dict[str, int] = {
    "1m": 86400,      # 1 day
    "5m": 86400,
    "15m": 86400,
    "30m": 86400,
    "60m": 86400,
    "1h": 86400,
    "1d": 604800,     # 7 days
    "1wk": 2592000,   # 30 days
}

DEFAULT_TTL = 86400  # 1 day fallback

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS historical_cache (
    key TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    interval TEXT NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    access_count INTEGER DEFAULT 0,
    last_accessed_at REAL NOT NULL,
    size_bytes INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_expires ON historical_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_last_accessed ON historical_cache(last_accessed_at);
"""


class HistoricalCache:
    """SQLite-backed cache for historical OHLCV data.

    Features:
    - TTL layering by interval (minute=1d, daily=7d, weekly=30d)
    - LRU eviction when total size exceeds max_size_mb
    - Thread-safe via WAL mode
    """

    def __init__(self, db_path: str, max_size_mb: int = 500):
        self._db_path = db_path
        self._max_size_bytes = max_size_mb * 1024 * 1024
        self._hit_count = 0
        self._miss_count = 0

        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()

    # ── public API ──────────────────────────────────────────────────

    def get(self, symbol: str, interval: str, start: str, end: str) -> dict | None:
        """Retrieve cached OHLCV data. Returns None on miss or expiry."""
        key = self._make_key(symbol, interval, start, end)
        now = time.time()

        row = self._conn.execute(
            "SELECT data, expires_at FROM historical_cache WHERE key = ?",
            (key,),
        ).fetchone()

        if row is None:
            self._miss_count += 1
            return None

        data_json, expires_at = row
        if now > expires_at:
            self._conn.execute("DELETE FROM historical_cache WHERE key = ?", (key,))
            self._conn.commit()
            self._miss_count += 1
            return None

        self._conn.execute(
            "UPDATE historical_cache SET access_count = access_count + 1, "
            "last_accessed_at = ? WHERE key = ?",
            (now, key),
        )
        self._conn.commit()
        self._hit_count += 1
        return json.loads(data_json)

    def put(
        self, symbol: str, interval: str, data: dict, start: str, end: str
    ) -> None:
        """Store OHLCV data with TTL based on interval."""
        key = self._make_key(symbol, interval, start, end)
        now = time.time()
        ttl = TTL_MAP.get(interval, DEFAULT_TTL)
        expires_at = now + ttl
        data_json = json.dumps(data)
        size_bytes = len(data_json.encode("utf-8"))

        self._conn.execute(
            "INSERT OR REPLACE INTO historical_cache "
            "(key, data, interval, created_at, expires_at, access_count, last_accessed_at, size_bytes) "
            "VALUES (?, ?, ?, ?, ?, 0, ?, ?)",
            (key, data_json, interval, now, expires_at, now, size_bytes),
        )
        self._conn.commit()

        self._check_size()

    def stats(self) -> dict:
        """Return cache statistics."""
        row = self._conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(size_bytes), 0) FROM historical_cache"
        ).fetchone()
        entry_count, total_size = row if row else (0, 0)
        total = self._hit_count + self._miss_count
        hit_rate = self._hit_count / total if total > 0 else 0.0
        return {
            "entry_count": entry_count,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "hit_count": self._hit_count,
            "miss_count": self._miss_count,
            "hit_rate": round(hit_rate, 4),
        }

    def evict_lru(self) -> int:
        """Evict oldest entries until under max_size_mb. Returns count evicted."""
        evicted = 0
        while True:
            row = self._conn.execute(
                "SELECT COALESCE(SUM(size_bytes), 0) FROM historical_cache"
            ).fetchone()
            total_size = row[0] if row else 0
            if total_size <= self._max_size_bytes:
                break

            oldest = self._conn.execute(
                "SELECT key FROM historical_cache ORDER BY last_accessed_at ASC LIMIT 1"
            ).fetchone()
            if oldest is None:
                break

            self._conn.execute(
                "DELETE FROM historical_cache WHERE key = ?", (oldest[0],)
            )
            evicted += 1

        if evicted:
            self._conn.commit()
            logger.info(f"LRU eviction: removed {evicted} entries")
        return evicted

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    # ── internal ────────────────────────────────────────────────────

    @staticmethod
    def _make_key(symbol: str, interval: str, start: str, end: str) -> str:
        return f"{symbol}:{interval}:{start}:{end}"

    def _check_size(self) -> None:
        """Check total size and evict if over limit."""
        row = self._conn.execute(
            "SELECT COALESCE(SUM(size_bytes), 0) FROM historical_cache"
        ).fetchone()
        total_size = row[0] if row else 0
        if total_size > self._max_size_bytes:
            self.evict_lru()

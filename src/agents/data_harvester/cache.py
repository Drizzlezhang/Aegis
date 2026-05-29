"""TTL-based 内存缓存 + LRU 淘汰。"""

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheEntry:
    data: Any
    created_at: float
    ttl_seconds: float

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl_seconds


class DataCache:
    DEFAULT_TTL = {"ohlcv": 300.0, "options_chain": 60.0, "quote": 15.0, "fundamentals": 3600.0}

    def __init__(self, max_entries: int = 500):
        self._store: dict[str, CacheEntry] = {}
        self._max = max_entries
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None
        if entry.is_expired:
            del self._store[key]
            self._misses += 1
            return None
        self._hits += 1
        return entry.data

    def put(self, key: str, data: Any, data_type: str = "ohlcv") -> None:
        if len(self._store) >= self._max:
            self._evict_oldest()
        ttl = self.DEFAULT_TTL.get(data_type, 300.0)
        self._store[key] = CacheEntry(data=data, created_at=time.time(), ttl_seconds=ttl)

    def invalidate(self, symbol: str) -> int:
        keys = [k for k in self._store if k.startswith(f"{symbol.upper()}:")]
        for k in keys:
            del self._store[k]
        return len(keys)

    def stats(self) -> dict:
        total = self._hits + self._misses
        return {"entries": len(self._store), "hits": self._hits, "misses": self._misses,
                "hit_rate": self._hits / total if total > 0 else 0.0}

    def _evict_oldest(self) -> None:
        if self._store:
            oldest = min(self._store, key=lambda k: self._store[k].created_at)
            del self._store[oldest]

    @staticmethod
    def make_key(symbol: str, data_type: str, **params) -> str:
        p = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{symbol.upper()}:{data_type}:{p}"

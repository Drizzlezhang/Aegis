"""Tests for DataCache."""

import time
import pytest
from src.agents.data_harvester.cache import DataCache


class TestDataCache:
    def test_get_returns_cached_data(self):
        c = DataCache(max_entries=10)
        c.put("NVDA:ohlcv:", [1, 2, 3])
        assert c.get("NVDA:ohlcv:") == [1, 2, 3]
        assert c.stats()["hits"] == 1

    def test_expired_entry_returns_none(self):
        c = DataCache(max_entries=10)
        key = "NVDA:ohlcv:"
        c.put(key, [1, 2, 3])
        c._store[key].created_at = time.time() - 9999
        c._store[key].ttl_seconds = 1.0
        assert c.get(key) is None
        assert c.stats()["misses"] == 1

    def test_lru_eviction_when_full(self):
        c = DataCache(max_entries=3)
        c.put("A:ohlcv:", "a")
        c.put("B:ohlcv:", "b")
        c.put("C:ohlcv:", "c")
        c.put("D:ohlcv:", "d")
        assert c.get("A:ohlcv:") is None  # oldest evicted
        assert c.get("B:ohlcv:") == "b"
        assert c.get("C:ohlcv:") == "c"
        assert c.get("D:ohlcv:") == "d"

    def test_invalidate_by_symbol(self):
        c = DataCache(max_entries=10)
        c.put("AAPL:ohlcv:", "data1")
        c.put("AAPL:fundamentals:", "data2")
        c.put("NVDA:ohlcv:", "data3")
        removed = c.invalidate("AAPL")
        assert removed == 2
        assert c.get("AAPL:ohlcv:") is None
        assert c.get("AAPL:fundamentals:") is None
        assert c.get("NVDA:ohlcv:") == "data3"

    def test_stats_accuracy(self):
        c = DataCache(max_entries=10)
        c.put("K1:ohlcv:", "v1")
        c.get("K1:ohlcv:")  # hit
        c.get("K2:ohlcv:")  # miss
        stats = c.stats()
        assert stats["entries"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5
"""Tests for HistoricalCache (B4)."""

import json
import tempfile
import time
from pathlib import Path

import pytest

from src.services.historical_cache import HistoricalCache


@pytest.fixture
def cache():
    """Create a temporary cache for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_cache.db"
        c = HistoricalCache(str(db_path), max_size_mb=1)
        yield c
        c.close()


class TestHistoricalCacheBasic:
    """Basic read/write tests."""

    def test_put_and_get(self, cache):
        data = {"close": [100, 101, 102], "open": [99, 100, 101]}
        cache.put("AAPL", "1d", data, "2024-01-01", "2024-01-03")
        result = cache.get("AAPL", "1d", "2024-01-01", "2024-01-03")
        assert result == data

    def test_miss_on_unknown_key(self, cache):
        result = cache.get("MSFT", "1d", "2024-01-01", "2024-01-03")
        assert result is None

    def test_different_intervals_independent(self, cache):
        data_daily = {"close": [100]}
        data_minute = {"close": [99]}
        cache.put("AAPL", "1d", data_daily, "2024-01-01", "2024-01-01")
        cache.put("AAPL", "1m", data_minute, "2024-01-01", "2024-01-01")
        assert cache.get("AAPL", "1d", "2024-01-01", "2024-01-01") == data_daily
        assert cache.get("AAPL", "1m", "2024-01-01", "2024-01-01") == data_minute

    def test_overwrite_existing_key(self, cache):
        data1 = {"close": [100]}
        data2 = {"close": [200]}
        cache.put("AAPL", "1d", data1, "2024-01-01", "2024-01-01")
        cache.put("AAPL", "1d", data2, "2024-01-01", "2024-01-01")
        assert cache.get("AAPL", "1d", "2024-01-01", "2024-01-01") == data2


class TestHistoricalCacheTTL:
    """TTL expiry tests."""

    def test_minute_interval_ttl(self, cache):
        """Minute data should expire after 1 day (simulated)."""
        data = {"close": [100]}
        cache.put("AAPL", "1m", data, "2024-01-01", "2024-01-01")

        # Manually expire by updating expires_at in DB
        cache._conn.execute(
            "UPDATE historical_cache SET expires_at = ? WHERE key LIKE 'AAPL:1m:%'",
            (time.time() - 1,),
        )
        cache._conn.commit()

        result = cache.get("AAPL", "1m", "2024-01-01", "2024-01-01")
        assert result is None

    def test_daily_interval_ttl(self, cache):
        """Daily data should expire after 7 days."""
        data = {"close": [100]}
        cache.put("AAPL", "1d", data, "2024-01-01", "2024-01-01")

        cache._conn.execute(
            "UPDATE historical_cache SET expires_at = ? WHERE key LIKE 'AAPL:1d:%'",
            (time.time() - 1,),
        )
        cache._conn.commit()

        result = cache.get("AAPL", "1d", "2024-01-01", "2024-01-01")
        assert result is None

    def test_weekly_interval_ttl(self, cache):
        """Weekly data should expire after 30 days."""
        data = {"close": [100]}
        cache.put("AAPL", "1wk", data, "2024-01-01", "2024-01-01")

        cache._conn.execute(
            "UPDATE historical_cache SET expires_at = ? WHERE key LIKE 'AAPL:1wk:%'",
            (time.time() - 1,),
        )
        cache._conn.commit()

        result = cache.get("AAPL", "1wk", "2024-01-01", "2024-01-01")
        assert result is None

    def test_not_expired_when_fresh(self, cache):
        data = {"close": [100]}
        cache.put("AAPL", "1d", data, "2024-01-01", "2024-01-01")
        result = cache.get("AAPL", "1d", "2024-01-01", "2024-01-01")
        assert result == data


class TestHistoricalCacheLRU:
    """LRU eviction tests."""

    def test_evict_when_over_limit(self, cache):
        """When total size exceeds max, oldest entries should be evicted."""
        # Create a cache with very small limit
        cache._max_size_bytes = 5000  # ~5KB

        # Insert many entries
        for i in range(200):
            data = {"close": [i] * 50}  # ~500 bytes each
            cache.put(f"SYM{i}", "1d", data, f"2024-01-{i+1:02d}", f"2024-01-{i+1:02d}")

        stats = cache.stats()
        total_size = stats["total_size_mb"] * 1024 * 1024
        assert total_size <= cache._max_size_bytes * 1.5  # Allow some slack

    def test_oldest_evicted_first(self, cache):
        cache._max_size_bytes = 5000

        # Insert first entry (oldest) — will be evicted
        cache.put("OLD", "1d", {"close": [1] * 200}, "2024-01-01", "2024-01-01")

        # Insert enough new entries to trigger eviction
        for i in range(20):
            cache.put(f"NEW{i}", "1d", {"close": [i] * 200}, f"2024-03-{i+1:02d}", f"2024-03-{i+1:02d}")

        # OLD should be evicted (oldest last_accessed_at, never accessed)
        result_old = cache.get("OLD", "1d", "2024-01-01", "2024-01-01")
        assert result_old is None

        # At least some new entries should survive
        stats = cache.stats()
        assert stats["entry_count"] > 0


class TestHistoricalCacheStats:
    """Statistics tests."""

    def test_initial_stats(self, cache):
        stats = cache.stats()
        assert stats["entry_count"] == 0
        assert stats["total_size_mb"] == 0.0
        assert stats["hit_count"] == 0
        assert stats["miss_count"] == 0
        assert stats["hit_rate"] == 0.0

    def test_hit_rate_after_operations(self, cache):
        data = {"close": [100]}
        cache.put("AAPL", "1d", data, "2024-01-01", "2024-01-01")

        # 9 hits, 1 miss
        for _ in range(9):
            cache.get("AAPL", "1d", "2024-01-01", "2024-01-01")
        cache.get("MISS", "1d", "2024-01-01", "2024-01-01")

        stats = cache.stats()
        assert stats["hit_count"] == 9
        assert stats["miss_count"] == 1
        assert stats["hit_rate"] == 0.9

    def test_high_hit_rate_with_1000_entries(self, cache):
        """Write 1000 entries, then read them all — hit_rate should be > 90%."""
        for i in range(1000):
            data = {"close": [i]}
            cache.put(f"SYM{i}", "1d", data, f"2024-01-{(i%28)+1:02d}", f"2024-01-{(i%28)+1:02d}")

        hits = 0
        misses = 0
        for i in range(1000):
            result = cache.get(f"SYM{i}", "1d", f"2024-01-{(i%28)+1:02d}", f"2024-01-{(i%28)+1:02d}")
            if result is not None:
                hits += 1
            else:
                misses += 1

        hit_rate = hits / (hits + misses) if (hits + misses) > 0 else 0
        assert hit_rate > 0.9, f"hit_rate={hit_rate}, hits={hits}, misses={misses}"


class TestHistoricalCachePerformance:
    """Performance tests."""

    def test_get_latency_under_5ms(self, cache):
        data = {"close": [100, 101, 102]}
        cache.put("AAPL", "1d", data, "2024-01-01", "2024-01-03")

        latencies = []
        for _ in range(100):
            start = time.monotonic()
            cache.get("AAPL", "1d", "2024-01-01", "2024-01-03")
            elapsed = (time.monotonic() - start) * 1000
            latencies.append(elapsed)

        avg_latency = sum(latencies) / len(latencies)
        assert avg_latency < 5.0, f"avg latency {avg_latency:.2f}ms exceeds 5ms"

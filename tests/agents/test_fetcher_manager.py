"""Tests for DataFetcherManager — 优先级降级、熔断器、缓存。"""

import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.data_harvester.base_fetcher import BaseFetcher, FetcherHealth, FetcherStatus
from src.agents.data_harvester.fetcher_manager import (
    CIRCUIT_FAILURE_THRESHOLD,
    CIRCUIT_OPEN_SECONDS,
    DataFetcherManager,
)
from src.config import DataSourceConfig


class MockFetcher(BaseFetcher):
    """Mock fetcher for testing."""

    def __init__(self, name: str, priority: int = 100, should_fail: bool = False):
        super().__init__(name=name, priority=priority)
        self._should_fail = should_fail
        self._ohlcv_calls = 0
        self._options_calls = 0
        self._health_calls = 0

    async def fetch_ohlcv(self, symbol: str, period: str = "1y"):
        self._ohlcv_calls += 1
        if self._should_fail:
            raise RuntimeError(f"{self.name} OHLCV failed")
        return {"symbol": symbol, "data": [{"close": 100.0}]}

    async def fetch_options_chain(self, symbol: str):
        self._options_calls += 1
        if self._should_fail:
            raise RuntimeError(f"{self.name} options failed")
        return {"symbol": symbol, "spot_price": 100.0}

    async def health_check(self):
        self._health_calls += 1
        if self._should_fail:
            return FetcherHealth(
                status=FetcherStatus.DOWN,
                latency_ms=0.0,
                error_count=3,
                last_error="failed",
            )
        return FetcherHealth(
            status=FetcherStatus.HEALTHY,
            latency_ms=10.0,
            error_count=0,
        )

    @property
    def ohlcv_calls(self):
        return self._ohlcv_calls


@pytest.fixture
def config():
    return DataSourceConfig(cache_ttl_seconds=300)


@pytest.fixture
def healthy_fetcher():
    return MockFetcher(name="healthy", priority=10)


@pytest.fixture
def failing_fetcher():
    return MockFetcher(name="failing", priority=20, should_fail=True)


@pytest.fixture
def low_priority_fetcher():
    return MockFetcher(name="low_priority", priority=50)


# --- 优先级降级 ---

@pytest.mark.asyncio
async def test_priority_order(config, healthy_fetcher, low_priority_fetcher):
    """高优先级 fetcher 优先使用。"""
    manager = DataFetcherManager([low_priority_fetcher, healthy_fetcher], config)
    result = await manager.fetch_ohlcv("QQQ")

    assert result["symbol"] == "QQQ"
    assert healthy_fetcher.ohlcv_calls == 1
    assert low_priority_fetcher.ohlcv_calls == 0  # 未被调用


@pytest.mark.asyncio
async def test_fallback_on_failure(config, failing_fetcher, low_priority_fetcher):
    """高优先级失败时降级到低优先级。"""
    manager = DataFetcherManager([failing_fetcher, low_priority_fetcher], config)
    result = await manager.fetch_ohlcv("QQQ")

    assert result["symbol"] == "QQQ"
    assert failing_fetcher.ohlcv_calls == 1
    assert low_priority_fetcher.ohlcv_calls == 1


@pytest.mark.asyncio
async def test_all_fetchers_fail(config, failing_fetcher):
    """所有 fetcher 失败时返回空 dict。"""
    manager = DataFetcherManager([failing_fetcher], config)
    result = await manager.fetch_ohlcv("QQQ")
    assert result == {}


# --- 熔断器 ---

@pytest.mark.asyncio
async def test_circuit_breaker_opens(config):
    """连续失败达阈值后熔断器打开，跳过该 fetcher。"""
    fetcher = MockFetcher(name="flaky", priority=10, should_fail=True)
    manager = DataFetcherManager([fetcher], config)

    # 连续失败直到熔断
    for _ in range(CIRCUIT_FAILURE_THRESHOLD):
        await manager.fetch_ohlcv("QQQ")

    circuit = manager._circuits["flaky"]
    assert circuit.status == "open"
    assert fetcher._health.status == FetcherStatus.DOWN


@pytest.mark.asyncio
async def test_circuit_breaker_skips_open(config):
    """熔断器打开时跳过该 fetcher。"""
    flaky = MockFetcher(name="flaky", priority=10, should_fail=True)
    backup = MockFetcher(name="backup", priority=20)
    manager = DataFetcherManager([flaky, backup], config)

    # 打开熔断器
    for _ in range(CIRCUIT_FAILURE_THRESHOLD):
        await manager.fetch_ohlcv("QQQ")

    # 熔断器打开后，flaky 不应再被调用
    flaky_calls_before = flaky.ohlcv_calls
    result = await manager.fetch_ohlcv("QQQ")

    assert result["symbol"] == "QQQ"
    assert flaky.ohlcv_calls == flaky_calls_before  # 未增加
    assert backup.ohlcv_calls >= 1


@pytest.mark.asyncio
async def test_circuit_breaker_half_open(config):
    """熔断器超时后进入半开状态。"""
    fetcher = MockFetcher(name="flaky", priority=10, should_fail=True)
    manager = DataFetcherManager([fetcher], config)

    # 打开熔断器
    for _ in range(CIRCUIT_FAILURE_THRESHOLD):
        await manager.fetch_ohlcv("QQQ")

    circuit = manager._circuits["flaky"]
    assert circuit.status == "open"

    # 模拟时间流逝
    circuit.open_until = time.monotonic() - 1  # 已过半开时间

    # 半开状态下会尝试调用
    result = await manager.fetch_ohlcv("QQQ")
    # 仍然失败，重新打开
    assert circuit.status == "open"


# --- 缓存 ---

@pytest.mark.asyncio
async def test_cache_hit(config, healthy_fetcher):
    """同一 symbol 短间隔内不重复请求。"""
    manager = DataFetcherManager([healthy_fetcher], config)

    result1 = await manager.fetch_ohlcv("QQQ")
    result2 = await manager.fetch_ohlcv("QQQ")

    assert result1 == result2
    assert healthy_fetcher.ohlcv_calls == 1  # 只调用一次


@pytest.mark.asyncio
async def test_cache_different_symbols(config, healthy_fetcher):
    """不同 symbol 各自缓存。"""
    manager = DataFetcherManager([healthy_fetcher], config)

    await manager.fetch_ohlcv("QQQ")
    await manager.fetch_ohlcv("SPY")

    assert healthy_fetcher.ohlcv_calls == 2


# --- 健康报告 ---

@pytest.mark.asyncio
async def test_health_report(config, healthy_fetcher, failing_fetcher):
    """健康报告包含所有 fetcher。"""
    manager = DataFetcherManager([healthy_fetcher, failing_fetcher], config)
    report = await manager.health_report()

    assert "healthy" in report
    assert "failing" in report
    assert report["healthy"].status == FetcherStatus.HEALTHY
    assert report["failing"].status == FetcherStatus.DOWN


# --- fetch_all ---

@pytest.mark.asyncio
async def test_fetch_all(config, healthy_fetcher):
    """fetch_all 返回所有数据类型。"""
    manager = DataFetcherManager([healthy_fetcher], config)
    result = await manager.fetch_all("QQQ")

    assert "ohlcv" in result
    assert "options_chain" in result
    assert "fundamentals" in result


# --- 退避 ---

@pytest.mark.asyncio
async def test_backoff_resets_on_success(config):
    """成功后退避重置。"""
    fetcher = MockFetcher(name="test", priority=10)
    manager = DataFetcherManager([fetcher], config)

    # 手动设置退避
    circuit = manager._circuits["test"]
    circuit.backoff_wait = 8.0

    await manager.fetch_ohlcv("QQQ")

    assert circuit.backoff_wait == 1.0  # 重置为初始值

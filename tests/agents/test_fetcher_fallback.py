"""DataFetcherManager fallback 链测试。"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.data_harvester.base_fetcher import BaseFetcher, FetcherHealth, FetcherStatus
from src.agents.data_harvester.fetcher_manager import (
    CircuitStatus,
    DataFetchError,
    DataFetcherManager,
)
from src.config import DataSourceConfig


class MockFetcher(BaseFetcher):
    """Mock fetcher for testing."""

    def __init__(self, name, priority=0, fail=False):
        super().__init__(name=name, priority=priority)
        self._fail = fail

    async def fetch_ohlcv(self, symbol, period="1y"):
        if self._fail:
            raise RuntimeError(f"{self.name} failed")
        return {"symbol": symbol, "data": []}

    async def fetch_options_chain(self, symbol):
        if self._fail:
            raise RuntimeError(f"{self.name} failed")
        return None

    async def health_check(self):
        return FetcherHealth(
            status=FetcherStatus.HEALTHY,
            latency_ms=10.0,
            error_count=0,
            last_error=None,
        )


@pytest.fixture
def config():
    return DataSourceConfig()


@pytest.mark.asyncio
async def test_fallback_chain_success_on_second(config):
    """第一个失败，第二个成功。"""
    f1 = MockFetcher("f1", priority=1, fail=True)
    f2 = MockFetcher("f2", priority=2, fail=False)
    manager = DataFetcherManager([f1, f2], config)

    result = await manager.fetch_with_fallback("QQQ", "fetch_ohlcv")

    assert result == {"symbol": "QQQ", "data": []}


@pytest.mark.asyncio
async def test_fallback_chain_all_fail(config):
    """全部失败时抛 DataFetchError。"""
    f1 = MockFetcher("f1", priority=1, fail=True)
    f2 = MockFetcher("f2", priority=2, fail=True)
    manager = DataFetcherManager([f1, f2], config)

    with pytest.raises(DataFetchError) as exc_info:
        await manager.fetch_with_fallback("QQQ", "fetch_ohlcv")

    assert "f1" in str(exc_info.value)
    assert "f2" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fallback_skips_open_circuit(config):
    """OPEN circuit 的 fetcher 被跳过。"""
    f1 = MockFetcher("f1", priority=1, fail=False)
    f2 = MockFetcher("f2", priority=2, fail=False)
    manager = DataFetcherManager([f1, f2], config)

    # 手动打开 f1 的熔断器
    manager._circuits["f1"].status = CircuitStatus.OPEN
    manager._circuits["f1"].open_until = float("inf")

    result = await manager.fetch_with_fallback("QQQ", "fetch_ohlcv")

    # 应该使用 f2
    assert result == {"symbol": "QQQ", "data": []}


@pytest.mark.asyncio
async def test_fetcher_metrics_recorded(config):
    """fetcher 调用后 metrics 被记录。"""
    f1 = MockFetcher("f1", priority=1, fail=False)
    manager = DataFetcherManager([f1], config)

    await manager.fetch_with_fallback("QQQ", "fetch_ohlcv")

    metrics = manager.get_fetcher_metrics()
    assert "f1" in metrics
    assert metrics["f1"].total_calls == 1
    assert metrics["f1"].success_count == 1
    assert metrics["f1"].error_count == 0


@pytest.mark.asyncio
async def test_fetcher_metrics_error_recorded(config):
    """fetcher 失败后 error metrics 被记录。"""
    f1 = MockFetcher("f1", priority=1, fail=True)
    manager = DataFetcherManager([f1], config)

    with pytest.raises(DataFetchError):
        await manager.fetch_with_fallback("QQQ", "fetch_ohlcv")

    metrics = manager.get_fetcher_metrics()
    assert metrics["f1"].total_calls == 1
    assert metrics["f1"].error_count == 1
    assert metrics["f1"].success_count == 0

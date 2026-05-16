"""Tests for BaseFetcher ABC and standardization."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.data_harvester.base_fetcher import (
    STANDARD_COLUMNS,
    BaseFetcher,
    FetcherHealth,
    FetcherStatus,
)


class ConcreteFetcher(BaseFetcher):
    """测试用具体 fetcher。"""

    def __init__(self):
        super().__init__(name="test", priority=50)

    async def fetch_ohlcv(self, symbol: str, period: str = "1y"):
        return {"symbol": symbol, "data": []}

    async def fetch_options_chain(self, symbol: str):
        return None

    async def health_check(self):
        return FetcherHealth(status=FetcherStatus.HEALTHY, latency_ms=10.0, error_count=0)


class FailingFetcher(BaseFetcher):
    """测试用失败 fetcher。"""

    def __init__(self):
        super().__init__(name="failing", priority=100)

    async def fetch_ohlcv(self, symbol: str, period: str = "1y"):
        raise RuntimeError("fetch failed")

    async def fetch_options_chain(self, symbol: str):
        raise RuntimeError("options failed")

    async def health_check(self):
        return FetcherHealth(status=FetcherStatus.DOWN, latency_ms=0.0, error_count=3, last_error="fetch failed")


def test_standard_columns():
    """STANDARD_COLUMNS 包含 9 个标准列。"""
    assert len(STANDARD_COLUMNS) == 9
    assert "date" in STANDARD_COLUMNS
    assert "open" in STANDARD_COLUMNS
    assert "close" in STANDARD_COLUMNS
    assert "volume" in STANDARD_COLUMNS
    assert "adj_close" in STANDARD_COLUMNS
    assert "dividend" in STANDARD_COLUMNS
    assert "split" in STANDARD_COLUMNS


def test_fetcher_status_enum():
    """FetcherStatus 枚举值正确。"""
    assert FetcherStatus.HEALTHY == "healthy"
    assert FetcherStatus.DEGRADED == "degraded"
    assert FetcherStatus.DOWN == "down"


def test_fetcher_health_defaults():
    """FetcherHealth 默认值。"""
    health = FetcherHealth()
    assert health.status == FetcherStatus.HEALTHY
    assert health.latency_ms == 0.0
    assert health.error_count == 0
    assert health.last_error is None


def test_cannot_instantiate_abc():
    """不能直接实例化 BaseFetcher。"""
    with pytest.raises(TypeError):
        BaseFetcher(name="direct")


def test_concrete_fetcher_instantiation():
    """具体子类可正常实例化。"""
    fetcher = ConcreteFetcher()
    assert fetcher.name == "test"
    assert fetcher.priority == 50
    assert fetcher.health.status == FetcherStatus.HEALTHY


@pytest.mark.asyncio
async def test_concrete_fetcher_methods():
    """具体子类方法可调用。"""
    fetcher = ConcreteFetcher()
    result = await fetcher.fetch_ohlcv("QQQ")
    assert result["symbol"] == "QQQ"

    options = await fetcher.fetch_options_chain("QQQ")
    assert options is None

    health = await fetcher.health_check()
    assert health.status == FetcherStatus.HEALTHY


def test_standardize_columns():
    """列名映射标准化。"""
    fetcher = ConcreteFetcher()
    raw = {
        "Date": "2024-01-01",
        "Open": 100.0,
        "High": 105.0,
        "Low": 98.0,
        "Close": 102.0,
        "Volume": 1000000,
        "Adj Close": 100.0,
        "Dividends": 0.5,
        "Stock Splits": 0.0,
        "extra_field": "kept",
    }
    result = fetcher.standardize_columns(raw)

    assert result["date"] == "2024-01-01"
    assert result["open"] == 100.0
    assert result["high"] == 105.0
    assert result["low"] == 98.0
    assert result["close"] == 102.0
    assert result["volume"] == 1000000
    assert result["adj_close"] == 100.0
    assert result["dividend"] == 0.5
    assert result["split"] == 0.0
    assert result["extra_field"] == "kept"


def test_standardize_columns_passthrough():
    """非字典输入原样返回。"""
    fetcher = ConcreteFetcher()
    assert fetcher.standardize_columns("not a dict") == "not a dict"
    assert fetcher.standardize_columns(None) is None

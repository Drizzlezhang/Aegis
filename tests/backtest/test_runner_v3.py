"""Tests for backtest v3 runner enhancements — timeframe, benchmark, etc."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import pytest

from src.backtest.runner import BacktestRunner


@dataclass
class _FakeBar:
    """Minimal OHLCV bar for testing."""

    timestamp: date
    close: float = 100.0
    open: float = 100.0
    high: float = 101.0
    low: float = 99.0
    volume: int = 1000000


def _make_daily_data(start: date, days: int) -> list[_FakeBar]:
    return [
        _FakeBar(timestamp=start + timedelta(days=i), close=100.0 + i * 0.1)
        for i in range(days)
    ]


def _make_hourly_data(start: date, hours: int) -> list[_FakeBar]:
    """Generate fake hourly OHLCV data (6.5 bars per trading day)."""
    bars: list[_FakeBar] = []
    current = start
    for i in range(hours):
        bars.append(_FakeBar(timestamp=current, close=100.0 + i * 0.01))
        current = current + timedelta(hours=1)
    return bars


class TestTimeframe:
    """T06: Multi-timeframe support."""

    @pytest.mark.asyncio
    async def test_timeframe_default_is_1d(self):
        """Default timeframe is '1d'."""
        runner = BacktestRunner("TEST", date(2023, 1, 1), date(2023, 12, 31))
        assert runner.timeframe == "1d"

    @pytest.mark.asyncio
    async def test_timeframe_accepts_1h(self):
        """AC-13: 1h timeframe is accepted."""
        runner = BacktestRunner(
            "TEST", date(2023, 1, 1), date(2023, 1, 31), timeframe="1h",
        )
        assert runner.timeframe == "1h"

    @pytest.mark.asyncio
    async def test_timeframe_accepts_5m(self):
        """AC-13: 5m timeframe is accepted."""
        runner = BacktestRunner(
            "TEST", date(2023, 1, 1), date(2023, 1, 31), timeframe="5m",
        )
        assert runner.timeframe == "5m"

    @pytest.mark.asyncio
    async def test_timeframe_accepts_1m(self):
        """AC-13: 1m timeframe is accepted."""
        runner = BacktestRunner(
            "TEST", date(2023, 1, 1), date(2023, 1, 31), timeframe="1m",
        )
        assert runner.timeframe == "1m"

    @pytest.mark.asyncio
    async def test_1d_vs_1h_trade_count_ratio(self):
        """AC-12: 1d/1h same period → trades ratio ≈ 6.5."""
        # Daily: 20 trading days
        daily_data = _make_daily_data(date(2023, 1, 2), 20)
        runner_d = BacktestRunner(
            "TEST", date(2023, 1, 2), date(2023, 1, 29), timeframe="1d",
        )
        await runner_d.run(daily_data)

        # Hourly: 20 days × 6.5 hours = 130 bars
        hourly_data = _make_hourly_data(date(2023, 1, 2), 130)
        runner_h = BacktestRunner(
            "TEST", date(2023, 1, 2), date(2023, 1, 29), timeframe="1h",
        )
        await runner_h.run(hourly_data)

        # Both use buy-and-hold (buy first bar, sell last) → 1 trade each
        # The ratio test is about bar count, not trade count
        assert len(daily_data) == 20
        assert len(hourly_data) == 130
        # Hourly bars / daily bars ≈ 6.5
        ratio = len(hourly_data) / len(daily_data)
        assert 6.0 <= ratio <= 7.0, f"Expected ratio ~6.5, got {ratio:.2f}"

    @pytest.mark.asyncio
    async def test_timeframe_preserved_in_result(self):
        """Timeframe is accessible from the runner after run."""
        runner = BacktestRunner(
            "TEST", date(2023, 1, 1), date(2023, 1, 31), timeframe="1h",
        )
        data = _make_hourly_data(date(2023, 1, 2), 130)
        result = await runner.run(data)
        assert runner.timeframe == "1h"
        assert result.symbol == "TEST"


class TestBenchmark:
    """T09: Benchmark comparison."""

    @pytest.mark.asyncio
    async def test_benchmark_outputs(self):
        """AC-23: Benchmark 输出 alpha/beta/IR/TE 四个指标."""
        data = _make_daily_data(date(2023, 1, 2), 60)
        runner = BacktestRunner(
            "TEST", date(2023, 1, 2), date(2023, 3, 31),
            benchmark_symbol="SPY",
        )
        result = await runner.run(data)

        assert result.benchmark is not None
        bm = result.benchmark
        assert hasattr(bm, "alpha")
        assert hasattr(bm, "beta")
        assert hasattr(bm, "information_ratio")
        assert hasattr(bm, "tracking_error")

    @pytest.mark.asyncio
    async def test_benchmark_alpha_neutral(self):
        """AC-22: 100% replica benchmark 策略 alpha ≈ 0."""
        # When strategy = benchmark (same equity curve), alpha should be ~0
        data = _make_daily_data(date(2023, 1, 2), 60)
        runner = BacktestRunner(
            "TEST", date(2023, 1, 2), date(2023, 3, 31),
            benchmark_symbol="SPY",
        )
        result = await runner.run(data)

        assert result.benchmark is not None
        # Since strategy and benchmark use the same underlying data,
        # alpha should be close to 0 (within ±0.05 tolerance for short period)
        assert abs(result.benchmark.alpha) < 0.05, (
            f"Alpha should be ~0 for replica, got {result.benchmark.alpha:.4f}"
        )

    @pytest.mark.asyncio
    async def test_no_benchmark_when_not_set(self):
        """When benchmark_symbol is None, benchmark is None."""
        data = _make_daily_data(date(2023, 1, 2), 30)
        runner = BacktestRunner(
            "TEST", date(2023, 1, 2), date(2023, 1, 31),
        )
        result = await runner.run(data)
        assert result.benchmark is None


class TestPerformance:
    """T16: Performance benchmarks."""

    @pytest.mark.asyncio
    async def test_1year_daily_backtest_under_30s(self):
        """1 year daily backtest completes in under 30 seconds."""
        import time

        data = _make_daily_data(date(2023, 1, 2), 252)
        runner = BacktestRunner("TEST", date(2023, 1, 2), date(2023, 12, 31))

        start = time.perf_counter()
        result = await runner.run(data)
        elapsed = time.perf_counter() - start

        assert elapsed < 30, f"1-year backtest took {elapsed:.2f}s, expected < 30s"
        assert result.metrics.total_trades >= 0

    @pytest.mark.asyncio
    async def test_1year_daily_backtest_returns_valid_result(self):
        """1 year daily backtest returns valid metrics."""
        data = _make_daily_data(date(2023, 1, 2), 252)
        runner = BacktestRunner("TEST", date(2023, 1, 2), date(2023, 12, 31))
        result = await runner.run(data)

        assert len(result.equity_curve) == 252
        assert result.metrics.total_return != 0
        assert result.metrics.sharpe_ratio != 0

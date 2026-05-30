"""Tests for walk_forward.py — WalkForwardRunner."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import pytest

from src.backtest.walk_forward import WalkForwardRunner
from src.models.backtest import WalkForwardConfig


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
    """Generate fake daily OHLCV data."""
    return [
        _FakeBar(timestamp=start + timedelta(days=i), close=100.0 + i * 0.1)
        for i in range(days)
    ]


class TestWalkForwardRunner:
    """T04/T05: WalkForwardRunner core functionality."""

    def test_import(self):
        """T04: import works."""
        from src.backtest.walk_forward import WalkForwardConfig, WalkForwardRunner
        assert WalkForwardRunner is not None
        assert WalkForwardConfig is not None

    @pytest.mark.asyncio
    async def test_rolling_fold_count(self):
        """AC-8: Rolling walk-forward 60d/20d/10d on 365 days → ~32 folds."""
        config = WalkForwardConfig(
            train_window_days=60,
            test_window_days=20,
            step_size_days=10,
            mode="rolling",
        )
        data = _make_daily_data(date(2023, 1, 1), 365)
        runner = WalkForwardRunner("TEST", config)
        result = await runner.run(data)

        # 365 - 60 - 20 = 285 days of sliding room, step 10 → ~28 folds
        # Actually: (365 - 80) / 10 = 28.5 → 28 folds
        assert 25 <= len(result.folds) <= 35, f"Expected ~28-32 folds, got {len(result.folds)}"

    @pytest.mark.asyncio
    async def test_anchored_fold_count(self):
        """AC-9: Anchored walk-forward fold count correct."""
        config = WalkForwardConfig(
            train_window_days=60,
            test_window_days=20,
            step_size_days=10,
            mode="anchored",
        )
        data = _make_daily_data(date(2023, 1, 1), 365)
        runner = WalkForwardRunner("TEST", config)
        result = await runner.run(data)

        # Anchored: train fixed at start, test slides
        # (365 - 60 - 20) / 10 = 28.5 → 28 folds
        assert 25 <= len(result.folds) <= 35, f"Expected ~28 folds, got {len(result.folds)}"

    @pytest.mark.asyncio
    async def test_no_lookahead_bias(self):
        """AC-10: No look-ahead bias — test data not in train."""
        config = WalkForwardConfig(
            train_window_days=60,
            test_window_days=20,
            step_size_days=20,
            mode="rolling",
        )
        data = _make_daily_data(date(2023, 1, 1), 200)
        runner = WalkForwardRunner("TEST", config)
        result = await runner.run(data)

        for fold in result.folds:
            # Test period must be strictly after train period
            assert fold.test_start > fold.train_end, (
                f"Fold {fold.fold_index}: test_start={fold.test_start} <= train_end={fold.train_end}"
            )
            # Train and test should not overlap
            assert fold.test_start > fold.train_end

    @pytest.mark.asyncio
    async def test_progress_callback(self):
        """AC-11: Progress callback fires once per fold."""
        config = WalkForwardConfig(
            train_window_days=60,
            test_window_days=20,
            step_size_days=20,
            mode="rolling",
        )
        data = _make_daily_data(date(2023, 1, 1), 200)
        runner = WalkForwardRunner("TEST", config)

        call_count = [0]

        def cb(current: int, total: int) -> None:
            call_count[0] += 1

        result = await runner.run(data, progress_callback=cb)
        assert call_count[0] == len(result.folds), (
            f"Callback called {call_count[0]} times, expected {len(result.folds)}"
        )

    @pytest.mark.asyncio
    async def test_insufficient_data_raises(self):
        """Edge case: insufficient data raises ValueError."""
        config = WalkForwardConfig(
            train_window_days=120,
            test_window_days=20,
            step_size_days=20,
            mode="rolling",
        )
        data = _make_daily_data(date(2023, 1, 1), 50)  # Only 50 days
        runner = WalkForwardRunner("TEST", config)

        with pytest.raises(ValueError, match="Insufficient data"):
            await runner.run(data)

    @pytest.mark.asyncio
    async def test_empty_data_raises(self):
        """Edge case: empty data raises ValueError."""
        config = WalkForwardConfig(
            train_window_days=60,
            test_window_days=20,
            step_size_days=20,
            mode="rolling",
        )
        runner = WalkForwardRunner("TEST", config)

        with pytest.raises(ValueError, match="No OHLCV data"):
            await runner.run([])

    @pytest.mark.asyncio
    async def test_single_fold(self):
        """Edge case: exactly one fold works."""
        config = WalkForwardConfig(
            train_window_days=60,
            test_window_days=20,
            step_size_days=100,  # Large step → only 1 fold
            mode="rolling",
        )
        data = _make_daily_data(date(2023, 1, 1), 100)
        runner = WalkForwardRunner("TEST", config)
        result = await runner.run(data)
        assert len(result.folds) == 1

    @pytest.mark.asyncio
    async def test_aggregate_metrics_present(self):
        """Aggregate metrics are computed from OOS equity curve."""
        config = WalkForwardConfig(
            train_window_days=60,
            test_window_days=20,
            step_size_days=20,
            mode="rolling",
        )
        data = _make_daily_data(date(2023, 1, 1), 200)
        runner = WalkForwardRunner("TEST", config)
        result = await runner.run(data)

        assert result.aggregate_metrics is not None
        assert result.oos_equity_curve is not None
        assert len(result.oos_equity_curve) > 0


class TestWalkForwardPerformance:
    """T16: Walk-forward performance benchmarks."""

    @pytest.mark.asyncio
    async def test_1year_walkforward_under_5min(self):
        """1 year walk-forward backtest completes in under 5 minutes."""
        import time

        config = WalkForwardConfig(
            train_window_days=60,
            test_window_days=20,
            step_size_days=20,
            mode="rolling",
        )
        data = _make_daily_data(date(2023, 1, 1), 365)
        runner = WalkForwardRunner("TEST", config)

        start = time.perf_counter()
        result = await runner.run(data)
        elapsed = time.perf_counter() - start

        assert elapsed < 300, f"1-year walk-forward took {elapsed:.2f}s, expected < 300s"
        assert len(result.folds) > 0

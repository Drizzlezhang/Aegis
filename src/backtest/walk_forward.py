"""Walk-forward backtest framework.

Splits historical data into rolling/anchored train/test windows,
runs BacktestRunner on each fold, and aggregates out-of-sample results.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

from src.backtest.runner import BacktestRunner
from src.models.backtest import (
    FoldResult,
    WalkForwardConfig,
    WalkForwardResult,
)

logger = logging.getLogger(__name__)


def _to_date(ts: Any) -> date:
    """Convert a timestamp to a date, handling both datetime and date objects."""
    from datetime import datetime as dt
    if isinstance(ts, dt):
        return ts.date()
    if isinstance(ts, date):
        return ts
    return ts.date()


class WalkForwardRunner:
    """Run walk-forward backtest over a date range.

    Splits data into train/test windows, runs BacktestRunner per fold,
    and aggregates out-of-sample results.

    Usage:
        config = WalkForwardConfig(
            train_window_days=120, test_window_days=20,
            step_size_days=20, mode="rolling",
        )
        runner = WalkForwardRunner("QQQ", config)
        result = await runner.run(ohlcv_data)
    """

    def __init__(
        self,
        symbol: str,
        config: WalkForwardConfig,
        strategy_config: dict[str, Any] | None = None,
    ) -> None:
        self.symbol = symbol.upper()
        self.config = config
        self.strategy_config = strategy_config or {}

    async def run(
        self,
        ohlcv_data: list[Any],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> WalkForwardResult:
        """Run walk-forward backtest.

        Args:
            ohlcv_data: Full OHLCV data (must have .timestamp with .date()).
            progress_callback: Called with (current_fold, total_folds).

        Returns:
            WalkForwardResult with folds and aggregate metrics.

        Raises:
            ValueError: If data is insufficient for the configured windows.
        """
        if not ohlcv_data:
            raise ValueError("No OHLCV data provided")

        # Sort by timestamp
        data = sorted(ohlcv_data, key=lambda b: b.timestamp)
        data_start = _to_date(data[0].timestamp)
        data_end = _to_date(data[-1].timestamp)
        total_days = (data_end - data_start).days

        min_required = self.config.train_window_days + self.config.test_window_days
        if total_days < min_required:
            raise ValueError(
                f"Insufficient data: {total_days} days available, "
                f"need at least {min_required} days "
                f"(train={self.config.train_window_days} + test={self.config.test_window_days})"
            )

        # Generate fold windows
        windows = self._generate_windows(data_start, data_end)
        total_folds = len(windows)

        folds: list[FoldResult] = []
        oos_equity_curve: list[dict[str, Any]] = []

        for fold_idx, (train_start, train_end, test_start, test_end) in enumerate(windows):
            # Split data
            train_data = [
                b for b in data
                if train_start <= _to_date(b.timestamp) <= train_end
            ]
            test_data = [
                b for b in data
                if test_start <= _to_date(b.timestamp) <= test_end
            ]

            # Run train
            train_runner = BacktestRunner(
                self.symbol, train_start, train_end, self.strategy_config,
            )
            train_result = await train_runner.run(train_data)

            # Run test
            test_runner = BacktestRunner(
                self.symbol, test_start, test_end, self.strategy_config,
            )
            test_result = await test_runner.run(test_data)

            fold = FoldResult(
                fold_index=fold_idx,
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                train_result=train_result,
                test_result=test_result,
            )
            folds.append(fold)

            # Append OOS equity curve (offset dates to avoid overlap confusion)
            for pt in test_result.equity_curve:
                oos_equity_curve.append(pt)

            logger.info(
                "Fold %d/%d: train_sharpe=%.2f, test_sharpe=%.2f",
                fold_idx + 1, total_folds,
                train_result.metrics.sharpe_ratio,
                test_result.metrics.sharpe_ratio,
            )

            if progress_callback:
                progress_callback(fold_idx + 1, total_folds)

        # Aggregate metrics from OOS equity curve
        from src.backtest.metrics import calculate_performance_report
        all_trades: list[Any] = []
        for f in folds:
            all_trades.extend(f.test_result.trades)
        aggregate_metrics = calculate_performance_report(oos_equity_curve, all_trades)

        return WalkForwardResult(
            symbol=self.symbol,
            config=self.config,
            folds=folds,
            aggregate_metrics=aggregate_metrics,
            oos_equity_curve=oos_equity_curve,
        )

    def _generate_windows(
        self, data_start: date, data_end: date,
    ) -> list[tuple[date, date, date, date]]:
        """Generate (train_start, train_end, test_start, test_end) tuples."""
        windows: list[tuple[date, date, date, date]] = []
        train_delta = timedelta(days=self.config.train_window_days)
        test_delta = timedelta(days=self.config.test_window_days)
        step_delta = timedelta(days=self.config.step_size_days)

        if self.config.mode == "anchored":
            # Train window anchored at data_start, test window slides forward
            train_start = data_start
            train_end = train_start + train_delta
            test_start = train_end + timedelta(days=1)
            test_end = test_start + test_delta

            while test_end <= data_end:
                windows.append((train_start, train_end, test_start, test_end))
                test_start = test_start + step_delta
                test_end = test_start + test_delta
        else:
            # Rolling: both train and test slide forward
            current = data_start
            while True:
                train_start = current
                train_end = train_start + train_delta
                test_start = train_end + timedelta(days=1)
                test_end = test_start + test_delta

                if test_end > data_end:
                    break

                windows.append((train_start, train_end, test_start, test_end))
                current = current + step_delta

        return windows

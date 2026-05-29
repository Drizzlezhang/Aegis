"""Pipeline backtest runner — feeds historical data through the agent pipeline."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import date, datetime as dt
from typing import Any

from src.models.backtest import (
    PipelineBacktestResult,
    PipelineBacktestTrade,
)

logger = logging.getLogger(__name__)


def _to_date(ts: Any) -> date:
    """Convert a timestamp to a date, handling both datetime and date objects."""
    if isinstance(ts, dt):
        return ts.date()
    if isinstance(ts, date):
        return ts
    return ts.date()


class BacktestRunner:
    """Run a full pipeline backtest over a historical date range.

    Feeds OHLCV data bar-by-bar through the Orchestrator pipeline,
    collects daily decisions, and simulates trades.
    """

    _BULLISH_PHASES: frozenset[str] = frozenset({"accumulation", "markup", "re_accumulation"})
    _BEARISH_PHASES: frozenset[str] = frozenset({"distribution", "markdown", "re_distribution"})

    def __init__(
        self,
        symbol: str,
        start: date,
        end: date,
        strategy_config: dict[str, Any] | None = None,
        timeframe: str = "1d",
        benchmark_symbol: str | None = None,
    ):
        self.symbol = symbol.upper()
        self.start = _to_date(start)
        self.end = _to_date(end)
        self.strategy_config = strategy_config or {}
        self.timeframe = timeframe
        self.benchmark_symbol = benchmark_symbol.upper() if benchmark_symbol else None

    async def run(
        self,
        ohlcv_data: list[Any],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> PipelineBacktestResult:
        """Run the backtest over provided OHLCV data.

        Args:
            ohlcv_data: List of OHLCV objects (must have .close, .timestamp).
            progress_callback: Called with (current, total) for progress.

        Returns:
            PipelineBacktestResult with equity curve, trades, and metrics.
        """
        if not ohlcv_data:
            return PipelineBacktestResult(
                symbol=self.symbol,
                strategy="pipeline",
                start_date=self.start,
                end_date=self.end,
            )

        # Filter by date range
        data = [
            d for d in ohlcv_data
            if self.start <= _to_date(d.timestamp) <= self.end
        ]
        if not data:
            return PipelineBacktestResult(
                symbol=self.symbol,
                strategy="pipeline",
                start_date=self.start,
                end_date=self.end,
            )

        total_bars = len(data)
        daily_decisions: list[dict[str, Any]] = []
        equity_curve: list[dict[str, Any]] = []
        trades: list[PipelineBacktestTrade] = []

        initial_capital = 100000.0
        capital = initial_capital
        shares = 0
        position_open = False
        current_trade: PipelineBacktestTrade | None = None

        # Benchmark: buy and hold
        first_price = data[0].close if hasattr(data[0], "close") else 0
        benchmark_shares = initial_capital / first_price if first_price > 0 else 0

        for i, bar in enumerate(data):
            price = bar.close if hasattr(bar, "close") else 0
            bar_date = _to_date(bar.timestamp)
            date_str = bar_date.isoformat()

            # Detect market phase
            prev_price = data[i - 1].close if i > 0 and hasattr(data[i - 1], "close") else None
            phase_name, phase_confidence = self._detect_phase(price, prev_price, i, total_bars)
            position_mult = self._calculate_position_size_multiplier(phase_name, phase_confidence)

            # Simulate a simple decision: buy on first bar, sell on last
            # In a real implementation, this would run the pipeline
            decision = self._simulate_decision(bar, i, total_bars)
            daily_decisions.append({
                "date": date_str,
                "price": price,
                "decision": decision,
                "phase": phase_name,
                "phase_confidence": phase_confidence,
                "position_size_multiplier": position_mult,
            })

            # Execute trades based on decision
            if decision == "buy" and not position_open:
                shares = int(capital / price) if price > 0 else 0
                if shares > 0:
                    capital -= shares * price
                    position_open = True
                    current_trade = PipelineBacktestTrade(
                        entry_date=date_str,
                        entry_price=price,
                        shares=shares,
                        status="open",
                        entry_phase=phase_name,
                        entry_confidence=phase_confidence,
                        position_size_multiplier=position_mult,
                    )

            elif decision == "sell" and position_open and current_trade:
                proceeds = shares * price
                capital += proceeds
                pnl = proceeds - (current_trade.shares * current_trade.entry_price)
                pnl_percent = (pnl / (current_trade.shares * current_trade.entry_price)) * 100
                current_trade.exit_date = date_str
                current_trade.exit_price = price
                current_trade.pnl = pnl
                current_trade.pnl_percent = pnl_percent
                current_trade.status = "closed"
                current_trade.exit_phase = phase_name
                current_trade.exit_confidence = phase_confidence
                trades.append(current_trade)
                shares = 0
                position_open = False
                current_trade = None

            # Record equity
            portfolio_value = capital + shares * price
            benchmark_value = benchmark_shares * price
            equity_curve.append({
                "date": date_str,
                "value": portfolio_value,
                "benchmark": benchmark_value,
            })

            if progress_callback:
                progress_callback(i + 1, total_bars)

        # Close any open position
        if position_open and current_trade:
            last_price = data[-1].close if hasattr(data[-1], "close") else 0
            last_date = _to_date(data[-1].timestamp).isoformat()
            last_phase, last_confidence = self._detect_phase(last_price, None, total_bars - 1, total_bars)
            proceeds = shares * last_price
            capital += proceeds
            pnl = proceeds - (current_trade.shares * current_trade.entry_price)
            pnl_percent = (pnl / (current_trade.shares * current_trade.entry_price)) * 100
            current_trade.exit_date = last_date
            current_trade.exit_price = last_price
            current_trade.pnl = pnl
            current_trade.pnl_percent = pnl_percent
            current_trade.status = "closed"
            current_trade.exit_phase = last_phase
            current_trade.exit_confidence = last_confidence
            trades.append(current_trade)
            equity_curve[-1]["value"] = capital

        # Calculate metrics
        from src.backtest.metrics import calculate_performance_report
        metrics = calculate_performance_report(equity_curve, trades)

        # Calculate benchmark metrics if benchmark_symbol is set
        benchmark_metrics = None
        if self.benchmark_symbol and equity_curve:
            benchmark_metrics = _calculate_benchmark_metrics(equity_curve)

        return PipelineBacktestResult(
            symbol=self.symbol,
            strategy="pipeline",
            start_date=self.start,
            end_date=self.end,
            equity_curve=equity_curve,
            trades=trades,
            metrics=metrics,
            daily_decisions=daily_decisions,
            benchmark=benchmark_metrics,
        )

    def _simulate_decision(self, bar: Any, index: int, total: int) -> str:
        """Simulate a trading decision for a single bar.

        In production, this would run the full Orchestrator pipeline.
        For now, uses a simple buy-and-hold strategy.
        """
        if index == 0:
            return "buy"
        if index == total - 1:
            return "sell"
        return "hold"

    def _detect_phase(self, price: float, prev_price: float | None, index: int, total: int) -> tuple[str, float]:
        """Detect market phase based on price action heuristics.

        Returns (phase_name, confidence).
        """
        if prev_price is None or prev_price == 0:
            return "accumulation", 50.0

        change_pct = (price - prev_price) / prev_price * 100
        position_ratio = index / max(total, 1)

        if position_ratio < 0.25:
            if change_pct > 0.5:
                return "markup", min(60.0 + abs(change_pct) * 5, 95.0)
            elif change_pct < -0.5:
                return "markdown", min(60.0 + abs(change_pct) * 5, 95.0)
            else:
                return "accumulation", 55.0
        elif position_ratio > 0.75:
            if change_pct > 0.5:
                return "re_accumulation", min(55.0 + abs(change_pct) * 3, 90.0)
            elif change_pct < -0.5:
                return "distribution", min(55.0 + abs(change_pct) * 3, 90.0)
            else:
                return "distribution", 50.0
        else:
            if change_pct > 1.0:
                return "markup", min(65.0 + abs(change_pct) * 3, 95.0)
            elif change_pct < -1.0:
                return "markdown", min(65.0 + abs(change_pct) * 3, 95.0)
            elif change_pct > 0:
                return "re_accumulation", 55.0
            else:
                return "re_distribution", 55.0

    def _calculate_position_size_multiplier(self, phase: str, confidence: float) -> float:
        """Calculate position size multiplier based on phase and confidence.

        Bullish phases get >1.0, bearish get <1.0.
        """
        base = 1.0
        if phase in self._BULLISH_PHASES:
            base = 1.0 + (confidence / 100.0) * 0.5  # 1.0 - 1.5
        elif phase in self._BEARISH_PHASES:
            base = 1.0 - (confidence / 100.0) * 0.5  # 0.5 - 1.0

        return round(base, 2)


class MultiSymbolRunner:
    """Run backtests for multiple symbols in parallel."""

    def __init__(
        self,
        symbols: list[str],
        start: date,
        end: date,
        max_concurrent: int = 3,
    ):
        self.symbols = [s.upper() for s in symbols]
        self.start = start
        self.end = end
        self.max_concurrent = max_concurrent

    async def run(
        self,
        ohlcv_data_map: dict[str, list[Any]],
        progress_callback: Callable[[str, int, int], None] | None = None,
    ) -> dict[str, PipelineBacktestResult]:
        """Run backtests for all symbols in parallel.

        Args:
            ohlcv_data_map: Symbol -> OHLCV data mapping.
            progress_callback: Called with (symbol, current, total).

        Returns:
            Dict mapping symbol to PipelineBacktestResult.
            Failed symbols are included with empty results.
        """
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def _run_one(symbol: str) -> PipelineBacktestResult:
            async with semaphore:
                try:
                    data = ohlcv_data_map.get(symbol, [])
                    runner = BacktestRunner(symbol, self.start, self.end)
                    return await runner.run(data)
                except Exception:
                    logger.exception("Backtest failed for %s", symbol)
                    return PipelineBacktestResult(
                        symbol=symbol,
                        strategy="pipeline",
                        start_date=self.start,
                        end_date=self.end,
                    )

        tasks = [_run_one(s) for s in self.symbols]
        results = await asyncio.gather(*tasks)
        return dict(zip(self.symbols, results, strict=False))


def _calculate_benchmark_metrics(equity_curve: list[dict[str, Any]]) -> "BenchmarkMetrics":
    """Calculate benchmark comparison metrics from equity curve.

    Uses the built-in benchmark values stored in each equity curve point.
    Computes alpha, beta, information ratio, and tracking error.

    Args:
        equity_curve: List of {"date", "value", "benchmark"} dicts.

    Returns:
        BenchmarkMetrics with alpha, beta, IR, TE.
    """
    from src.models.backtest import BenchmarkMetrics

    if len(equity_curve) < 2:
        return BenchmarkMetrics()

    # Extract daily returns
    strategy_returns: list[float] = []
    benchmark_returns: list[float] = []

    for i in range(1, len(equity_curve)):
        prev_val = equity_curve[i - 1]["value"]
        curr_val = equity_curve[i]["value"]
        prev_bm = equity_curve[i - 1].get("benchmark", prev_val)
        curr_bm = equity_curve[i].get("benchmark", curr_val)

        if prev_val > 0:
            strategy_returns.append((curr_val - prev_val) / prev_val)
        if prev_bm > 0:
            benchmark_returns.append((curr_bm - prev_bm) / prev_bm)

    if not strategy_returns or not benchmark_returns:
        return BenchmarkMetrics()

    n = min(len(strategy_returns), len(benchmark_returns))
    sr = strategy_returns[:n]
    br = benchmark_returns[:n]

    # Beta = Cov(s, b) / Var(b)
    mean_s = sum(sr) / n
    mean_b = sum(br) / n

    cov = sum((s - mean_s) * (b - mean_b) for s, b in zip(sr, br, strict=False)) / n
    var_b = sum((b - mean_b) ** 2 for b in br) / n

    beta = cov / var_b if var_b > 0 else 1.0

    # Alpha = mean_s - beta * mean_b (daily, annualized later)
    alpha_daily = mean_s - beta * mean_b
    alpha = alpha_daily * 252  # Annualize

    # Tracking error = std(s - b) * sqrt(252)
    diffs = [s - b for s, b in zip(sr, br, strict=False)]
    mean_diff = sum(diffs) / n
    var_diff = sum((d - mean_diff) ** 2 for d in diffs) / n
    tracking_error = (var_diff ** 0.5) * (252 ** 0.5)

    # Information ratio = alpha / tracking_error
    information_ratio = alpha / tracking_error if tracking_error > 0 else 0.0

    # Total returns
    strategy_return = (equity_curve[-1]["value"] / equity_curve[0]["value"] - 1) if equity_curve[0]["value"] > 0 else 0.0
    benchmark_return = (equity_curve[-1].get("benchmark", equity_curve[-1]["value"]) / equity_curve[0].get("benchmark", equity_curve[0]["value"]) - 1) if equity_curve[0].get("benchmark", 1) > 0 else 0.0

    return BenchmarkMetrics(
        alpha=alpha,
        beta=beta,
        information_ratio=information_ratio,
        tracking_error=tracking_error,
        benchmark_return=benchmark_return,
        strategy_return=strategy_return,
    )

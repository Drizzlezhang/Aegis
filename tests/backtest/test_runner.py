"""Tests for BacktestRunner and MultiSymbolRunner."""

from dataclasses import dataclass
from datetime import date, datetime

import pytest

from src.backtest.runner import BacktestRunner, MultiSymbolRunner
from src.models.backtest import PipelineBacktestResult


@dataclass
class MockOHLCV:
    """Mock OHLCV bar for testing."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int = 0


def _make_ohlcv_data(n_days: int = 60, start_price: float = 100.0) -> list[MockOHLCV]:
    """Generate mock OHLCV data for n trading days."""
    import random
    random.seed(42)
    data = []
    price = start_price
    base_date = datetime(2024, 1, 2)
    for i in range(n_days):
        change = random.uniform(-2, 2)
        price += change
        if price < 1:
            price = 1
        ts = base_date.replace(day=min(base_date.day + i, 28))
        data.append(MockOHLCV(
            timestamp=ts,
            open=price - 0.5,
            high=price + 1,
            low=price - 1,
            close=price,
            volume=10000,
        ))
    return data


class TestBacktestRunner:
    """Tests for BacktestRunner."""

    @pytest.mark.asyncio
    async def test_result_structure(self):
        """BacktestResult has correct structure."""
        data = _make_ohlcv_data(60)
        runner = BacktestRunner("QQQ", date(2024, 1, 1), date(2024, 3, 31))
        result = await runner.run(data)

        assert isinstance(result, PipelineBacktestResult)
        assert result.symbol == "QQQ"
        assert len(result.equity_curve) > 0
        assert len(result.daily_decisions) > 0
        assert result.metrics.total_trades >= 0

    @pytest.mark.asyncio
    async def test_equity_curve_length(self):
        """Equity curve length equals number of trading days."""
        data = _make_ohlcv_data(30)
        runner = BacktestRunner("SPY", date(2024, 1, 1), date(2024, 2, 28))
        result = await runner.run(data)

        assert len(result.equity_curve) == len(data)

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """Empty data returns empty result without crashing."""
        runner = BacktestRunner("QQQ", date(2024, 1, 1), date(2024, 3, 31))
        result = await runner.run([])

        assert result.symbol == "QQQ"
        assert len(result.equity_curve) == 0
        assert len(result.trades) == 0

    @pytest.mark.asyncio
    async def test_progress_callback(self):
        """Progress callback is invoked with correct counts."""
        data = _make_ohlcv_data(10)
        progress_calls: list[tuple[int, int]] = []

        def cb(current: int, total: int):
            progress_calls.append((current, total))

        runner = BacktestRunner("QQQ", date(2024, 1, 1), date(2024, 1, 31))
        await runner.run(data, progress_callback=cb)

        assert len(progress_calls) == 10
        assert progress_calls[-1] == (10, 10)

    @pytest.mark.asyncio
    async def test_historical_mode_no_http(self):
        """Orchestrator historical_mode flag is set correctly."""
        from src.agents.orchestrator import Orchestrator

        orch = Orchestrator()
        orch.historical_mode = True
        orch.set_historical_data("QQQ", _make_ohlcv_data(5))

        assert orch.historical_mode is True
        assert len(orch.get_historical_data("QQQ")) == 5
        assert len(orch.get_historical_data("UNKNOWN")) == 0


class TestMultiSymbolRunner:
    """Tests for MultiSymbolRunner."""

    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Multi-symbol backtest runs all symbols."""
        data_map = {
            "QQQ": _make_ohlcv_data(10),
            "SPY": _make_ohlcv_data(10),
            "NVDA": _make_ohlcv_data(10),
        }
        runner = MultiSymbolRunner(
            ["QQQ", "SPY", "NVDA"],
            date(2024, 1, 1),
            date(2024, 1, 31),
            max_concurrent=3,
        )
        results = await runner.run(data_map)

        assert len(results) == 3
        for symbol in ["QQQ", "SPY", "NVDA"]:
            assert symbol in results
            assert results[symbol].symbol == symbol

    @pytest.mark.asyncio
    async def test_single_failure_does_not_block_others(self):
        """One symbol failing doesn't affect others."""
        data_map = {
            "QQQ": _make_ohlcv_data(10),
            "SPY": [],  # empty data
            "NVDA": _make_ohlcv_data(10),
        }
        runner = MultiSymbolRunner(
            ["QQQ", "SPY", "NVDA"],
            date(2024, 1, 1),
            date(2024, 1, 31),
            max_concurrent=3,
        )
        results = await runner.run(data_map)

        assert len(results) == 3
        assert results["QQQ"].symbol == "QQQ"
        assert results["NVDA"].symbol == "NVDA"
        # SPY should still be present (empty result)
        assert results["SPY"].symbol == "SPY"


class TestPhaseAware:
    """Tests for phase-aware backtest decisions."""

    @pytest.mark.asyncio
    async def test_trades_have_phase_info(self):
        """Trades record entry_phase and entry_confidence."""
        data = _make_ohlcv_data(60)
        runner = BacktestRunner("QQQ", date(2024, 1, 1), date(2024, 3, 31))
        result = await runner.run(data)

        for trade in result.trades:
            assert trade.entry_phase is not None, f"Trade missing entry_phase: {trade}"
            assert trade.entry_confidence is not None, f"Trade missing entry_confidence: {trade}"
            assert trade.exit_phase is not None, f"Trade missing exit_phase: {trade}"
            assert trade.exit_confidence is not None, f"Trade missing exit_confidence: {trade}"

    @pytest.mark.asyncio
    async def test_daily_decisions_have_phase_info(self):
        """Daily decisions include phase and confidence."""
        data = _make_ohlcv_data(30)
        runner = BacktestRunner("SPY", date(2024, 1, 1), date(2024, 2, 28))
        result = await runner.run(data)

        for d in result.daily_decisions:
            assert "phase" in d
            assert "phase_confidence" in d
            assert "position_size_multiplier" in d

    @pytest.mark.asyncio
    async def test_position_size_multiplier_range(self):
        """Position size multiplier is between 0.5 and 1.5."""
        data = _make_ohlcv_data(60)
        runner = BacktestRunner("QQQ", date(2024, 1, 1), date(2024, 3, 31))
        result = await runner.run(data)

        for d in result.daily_decisions:
            mult = d["position_size_multiplier"]
            assert 0.5 <= mult <= 1.5, f"Multiplier out of range: {mult}"

    def test_detect_phase_returns_valid_phases(self):
        """_detect_phase returns valid Wyckoff phase names."""
        runner = BacktestRunner("QQQ", date(2024, 1, 1), date(2024, 3, 31))
        valid_phases = {
            "accumulation", "markup", "distribution",
            "markdown", "re_accumulation", "re_distribution",
        }

        phase, conf = runner._detect_phase(100.0, 98.0, 5, 60)
        assert phase in valid_phases
        assert 0 <= conf <= 100

    def test_detect_phase_no_prev_price(self):
        """_detect_phase with no previous price returns accumulation."""
        runner = BacktestRunner("QQQ", date(2024, 1, 1), date(2024, 3, 31))
        phase, conf = runner._detect_phase(100.0, None, 0, 60)
        assert phase == "accumulation"
        assert conf == 50.0

    def test_calculate_position_size_multiplier_bullish(self):
        """Bullish phases get multiplier >= 1.0."""
        runner = BacktestRunner("QQQ", date(2024, 1, 1), date(2024, 3, 31))
        mult = runner._calculate_position_size_multiplier("markup", 80.0)
        assert mult >= 1.0

    def test_calculate_position_size_multiplier_bearish(self):
        """Bearish phases get multiplier <= 1.0."""
        runner = BacktestRunner("QQQ", date(2024, 1, 1), date(2024, 3, 31))
        mult = runner._calculate_position_size_multiplier("markdown", 80.0)
        assert mult <= 1.0

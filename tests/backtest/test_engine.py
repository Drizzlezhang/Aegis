"""Tests for backtest engine."""

from datetime import date, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.backtest.engine import BacktestEngine, TradeRecord
from src.backtest.strategies import Signal


class TestBacktestEngine:
    """Tests for BacktestEngine."""

    def setup_method(self):
        """Create engine instance for each test."""
        self.engine = BacktestEngine(short_window=2, long_window=3)

    @pytest.fixture
    def mock_ohlcv_data(self):
        """Create mock OHLCV data for testing."""
        return [
            Mock(timestamp=datetime(2024, 1, i + 1), close=100.0 + i * 2, volume=1000000)
            for i in range(10)
        ]

    @pytest.mark.asyncio
    async def test_run_backtest_success(self, mock_ohlcv_data):
        """Successful backtest returns BacktestResult."""
        with patch.object(
            self.engine, "_fetch_ohlcv", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = mock_ohlcv_data

            result = await self.engine.run_backtest(
                symbol="QQQ",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 10),
                initial_capital=100000.0,
            )

            assert result.symbol == "QQQ"
            assert result.strategy == "SMA2/3"
            assert len(result.equity_curve) == 10
            assert result.equity_curve[0]["value"] == 100000.0

    @pytest.mark.asyncio
    async def test_run_backtest_no_data(self):
        """No data raises ValueError."""
        with patch.object(
            self.engine, "_fetch_ohlcv", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = []

            with pytest.raises(ValueError, match="No data available"):
                await self.engine.run_backtest(
                    symbol="QQQ",
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 10),
                )

    @pytest.mark.asyncio
    async def test_run_backtest_insufficient_data(self):
        """Insufficient data raises ValueError."""
        short_data = [
            Mock(timestamp=datetime(2024, 1, i + 1), close=100.0, volume=1000000)
            for i in range(3)
        ]
        with patch.object(
            self.engine, "_fetch_ohlcv", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = short_data

            with pytest.raises(ValueError, match="Insufficient data"):
                await self.engine.run_backtest(
                    symbol="QQQ",
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 3),
                )

    def test_simulate_buy_signal(self):
        """Buy signal triggers entry trade."""
        from src.models import OHLCV

        ohlcv_data = [
            OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, 1), open=100, high=101, low=99, close=100, volume=1000),
            OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, 2), open=100, high=101, low=99, close=101, volume=1000),
            OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, 3), open=100, high=101, low=99, close=102, volume=1000),
            OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, 4), open=100, high=101, low=99, close=105, volume=1000),
            OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, 5), open=100, high=101, low=99, close=106, volume=1000),
        ]
        signals = [Signal(date="2024-01-04", action="buy")]

        equity, trades = self.engine._simulate(
            ohlcv_data, signals, 100000.0
        )

        assert len(trades) >= 1
        assert trades[0].status == "closed"
        assert trades[0].entry_price == 105.0

    def test_simulate_buy_and_sell_signals(self):
        """Buy then sell signals trigger a complete trade cycle."""
        from src.models import OHLCV

        ohlcv_data = [
            OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, 1), open=100, high=101, low=99, close=100, volume=1000),
            OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, 2), open=100, high=101, low=99, close=101, volume=1000),
            OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, 3), open=100, high=101, low=99, close=102, volume=1000),
            OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, 4), open=100, high=101, low=99, close=105, volume=1000),
            OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, 5), open=100, high=101, low=99, close=106, volume=1000),
            OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, 6), open=100, high=101, low=99, close=95, volume=1000),
        ]
        signals = [
            Signal(date="2024-01-04", action="buy"),
            Signal(date="2024-01-06", action="sell"),
        ]

        equity, trades = self.engine._simulate(
            ohlcv_data, signals, 100000.0
        )

        # Should have completed a buy-and-sell cycle
        closed_trades = [t for t in trades if t.status == "closed"]
        assert len(closed_trades) >= 1

    def test_simulate_closes_open_position_at_end(self):
        """Open position at end of period is closed automatically."""
        from src.models import OHLCV

        ohlcv_data = [
            OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, 1), open=100, high=101, low=99, close=100, volume=1000),
            OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, 2), open=100, high=101, low=99, close=101, volume=1000),
            OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, 3), open=100, high=101, low=99, close=102, volume=1000),
            OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, 4), open=100, high=101, low=99, close=105, volume=1000),
        ]
        # Buy signal but no sell signal before end
        signals = [Signal(date="2024-01-04", action="buy")]

        equity, trades = self.engine._simulate(
            ohlcv_data, signals, 100000.0
        )

        # Should close the open position at the last day
        assert len(trades) == 1
        assert trades[0].status == "closed"
        assert trades[0].exit_date == "2024-01-04"

    def test_date_range_to_period(self):
        """Date range correctly mapped to yfinance period strings."""
        assert self.engine._date_range_to_period(
            date(2024, 1, 1), date(2024, 1, 5)
        ) == "1mo"
        assert self.engine._date_range_to_period(
            date(2024, 1, 1), date(2024, 1, 30)
        ) == "3mo"
        assert self.engine._date_range_to_period(
            date(2024, 1, 1), date(2024, 3, 31)
        ) == "6mo"
        # Jan 1 to Jun 30 is 181 days (2024 is leap year), falls into 2y bucket
        assert self.engine._date_range_to_period(
            date(2024, 1, 1), date(2024, 6, 30)
        ) == "2y"
        assert self.engine._date_range_to_period(
            date(2024, 1, 1), date(2024, 12, 31)
        ) == "2y"
        assert self.engine._date_range_to_period(
            date(2024, 1, 1), date(2025, 12, 31)
        ) == "5y"
        assert self.engine._date_range_to_period(
            date(2020, 1, 1), date(2025, 12, 31)
        ) == "max"


class TestTradeRecord:
    """Tests for TradeRecord dataclass."""

    def test_default_values(self):
        """Default values set correctly."""
        trade = TradeRecord(entry_date="2024-01-01")
        assert trade.entry_date == "2024-01-01"
        assert trade.exit_date is None
        assert trade.entry_price == 0.0
        assert trade.exit_price is None
        assert trade.shares == 0
        assert trade.pnl is None
        assert trade.pnl_percent is None
        assert trade.status == "open"

    def test_closed_trade(self):
        """Closed trade has all fields."""
        trade = TradeRecord(
            entry_date="2024-01-01",
            exit_date="2024-01-10",
            entry_price=100.0,
            exit_price=110.0,
            shares=100,
            pnl=1000.0,
            pnl_percent=10.0,
            status="closed",
        )
        assert trade.exit_date == "2024-01-10"
        assert trade.pnl == 1000.0
        assert trade.status == "closed"


class TestBacktestEngineRsi:
    """End-to-end tests for RSI signal type."""

    @pytest.mark.asyncio
    async def test_run_backtest_rsi_signal(self):
        """RSI signal type produces backtest result."""
        engine = BacktestEngine(
            signal_type="rsi",
            rsi_period=14,
            rsi_oversold=30.0,
            rsi_overbought=70.0,
        )

        # Need at least long_window + 5 = 55 data points for engine check
        mock_data = [
            Mock(timestamp=datetime(2024, 1, 1) + __import__("datetime").timedelta(days=i), close=100.0 + i * 2, volume=1000000)
            for i in range(60)
        ]
        with patch.object(engine, "_fetch_ohlcv", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data

            result = await engine.run_backtest(
                symbol="QQQ",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 3, 1),
                initial_capital=100000.0,
            )

            assert result.symbol == "QQQ"
            assert len(result.equity_curve) == 60


class TestBacktestEngineCombo:
    """End-to-end tests for SMA+RSI combo signal type."""

    @pytest.mark.asyncio
    async def test_run_backtest_combo_signal(self):
        """Combo signal type produces backtest result."""
        engine = BacktestEngine(
            short_window=2,
            long_window=3,
            signal_type="sma_rsi_combo",
            rsi_period=14,
            rsi_oversold=30.0,
            rsi_overbought=70.0,
        )

        mock_data = [
            Mock(timestamp=datetime(2024, 1, i + 1), close=100.0 + i * 2, volume=1000000)
            for i in range(30)
        ]
        with patch.object(engine, "_fetch_ohlcv", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data

            result = await engine.run_backtest(
                symbol="QQQ",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 30),
                initial_capital=100000.0,
            )

            assert result.symbol == "QQQ"
            assert len(result.equity_curve) == 30

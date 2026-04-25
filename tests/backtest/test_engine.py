"""Tests for backtest engine."""

from datetime import date, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.backtest.engine import BacktestEngine, TradeRecord


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

    def test_calculate_sma(self):
        """SMA calculation produces correct values."""
        prices = [1.0, 2.0, 3.0, 4.0, 5.0]
        sma = BacktestEngine._calculate_sma(prices, window=3)

        assert sma[0] is None
        assert sma[1] is None
        assert sma[2] == pytest.approx(2.0)
        assert sma[3] == pytest.approx(3.0)
        assert sma[4] == pytest.approx(4.0)

    def test_calculate_sma_window_equals_length(self):
        """SMA with window equal to data length."""
        prices = [10.0, 20.0, 30.0]
        sma = BacktestEngine._calculate_sma(prices, window=3)

        assert sma[0] is None
        assert sma[1] is None
        assert sma[2] == pytest.approx(20.0)

    def test_simulate_golden_cross_buy(self):
        """Golden cross (short SMA crosses above long SMA) triggers buy."""
        from src.models import OHLCV

        ohlcv_data = [
            OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, 1), open=100, high=101, low=99, close=100, volume=1000),
            OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, 2), open=100, high=101, low=99, close=101, volume=1000),
            OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, 3), open=100, high=101, low=99, close=102, volume=1000),
            OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, 4), open=100, high=101, low=99, close=105, volume=1000),  # golden cross
            OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, 5), open=100, high=101, low=99, close=106, volume=1000),
        ]
        # short=2: [None, 100.5, 101.5, 103.5, 105.5]
        # long=3:  [None, None, 101.0, 102.67, 104.33]
        short_sma = [None, 100.5, 101.5, 103.5, 105.5]
        long_sma = [None, None, 101.0, 102.67, 104.33]

        equity, trades = self.engine._simulate(
            ohlcv_data, short_sma, long_sma, 100000.0
        )

        # Golden cross at i=3: prev_short=101.5 <= prev_long=101.0 is False
        # At i=4: prev_short=103.5 > prev_long=102.67, short=105.5 > long=104.33
        # Need a clearer crossover - let's use explicit values
        short_sma2 = [None, 99.0, 100.0, 103.0, 106.0]
        long_sma2 = [None, None, 100.5, 101.0, 104.0]

        equity, trades = self.engine._simulate(
            ohlcv_data, short_sma2, long_sma2, 100000.0
        )

        # Crossover at i=3: prev_short=100.0 <= prev_long=100.5, short=103.0 > long=101.0 -> BUY
        assert len(trades) >= 1
        assert trades[0].status == "closed"
        assert trades[0].entry_price == 105.0

    def test_simulate_death_cross_sell(self):
        """Death cross (short SMA crosses below long SMA) triggers sell."""
        from src.models import OHLCV

        ohlcv_data = [
            OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, 1), open=100, high=101, low=99, close=100, volume=1000),
            OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, 2), open=100, high=101, low=99, close=101, volume=1000),
            OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, 3), open=100, high=101, low=99, close=102, volume=1000),
            OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, 4), open=100, high=101, low=99, close=105, volume=1000),
            OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, 5), open=100, high=101, low=99, close=106, volume=1000),
            OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, 6), open=100, high=101, low=99, close=95, volume=1000),
        ]
        # Golden cross at i=3, death cross at i=5
        short_sma = [None, 99.0, 100.0, 103.0, 105.5, 100.5]
        long_sma = [None, None, 100.5, 101.0, 104.33, 102.0]

        equity, trades = self.engine._simulate(
            ohlcv_data, short_sma, long_sma, 100000.0
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
        # Golden cross at i=3, no death cross before end
        short_sma = [None, 99.0, 100.0, 103.0]
        long_sma = [None, None, 100.5, 101.0]

        equity, trades = self.engine._simulate(
            ohlcv_data, short_sma, long_sma, 100000.0
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

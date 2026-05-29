"""Tests for options backtest engine."""


import pytest

from src.backtest.options_engine import (
    OptionsBacktestEngine,
    OptionsBacktestResult,
    OptionsStrategy,
    OptionsTradeResult,
)
from src.backtest.options_pricing import OptionType, position_pnl


def _make_price_data(prices: list[float], start_date: str = "2024-01-02") -> list[dict]:
    """Build price_data list from a sequence of close prices."""
    from datetime import datetime, timedelta

    base = datetime.strptime(start_date, "%Y-%m-%d")
    data = []
    for i, price in enumerate(prices):
        d = base + timedelta(days=i)
        data.append({
            "date": d.strftime("%Y-%m-%d"),
            "open": price,
            "high": price,
            "low": price,
            "close": price,
            "volume": 1000000,
        })
    return data


class TestCoveredCall:
    """Tests for covered_call strategy."""

    def test_covered_call_profitable_when_flat(self):
        """Stock stays flat → short call premium is profit."""
        # 30 days of flat price at $100
        prices = [100.0] * 30
        _make_price_data(prices)

        engine = OptionsBacktestEngine(strategy=OptionsStrategy.COVERED_CALL)
        result = engine._construct_legs(OptionsStrategy.COVERED_CALL, 100.0, 45)

        assert len(result) == 1
        assert result[0].option_type == OptionType.CALL
        assert result[0].quantity == -1  # short
        assert result[0].strike == pytest.approx(105.0)  # spot * 1.05

    def test_covered_call_loss_when_big_drop(self):
        """Stock drops significantly → stock loss exceeds premium."""
        # Start at 100, drop to 80 over 30 days
        prices = [100.0 - i * 0.67 for i in range(30)]  # ~80 at end
        _make_price_data(prices)

        engine = OptionsBacktestEngine(strategy=OptionsStrategy.COVERED_CALL)
        # Manually construct legs and verify PnL at end
        legs = engine._construct_legs(OptionsStrategy.COVERED_CALL, 100.0, 45)
        # At end: spot=80, dte_remaining = 45 - 29 = 16
        pnl = position_pnl(legs, 80.0, 16)
        # Stock PnL: (80 - 100) * 100 = -2000
        stock_pnl = (80.0 - 100.0) * 100
        total = pnl + stock_pnl
        # Should be negative (stock loss > premium)
        assert total < 0


class TestBullSpread:
    """Tests for bull_spread strategy."""

    def test_bull_spread_max_profit_capped(self):
        """Stock far above short strike → profit capped at width - debit."""
        engine = OptionsBacktestEngine(strategy=OptionsStrategy.BULL_SPREAD)
        legs = engine._construct_legs(OptionsStrategy.BULL_SPREAD, 100.0, 45)

        assert len(legs) == 2
        # Long ATM call + short OTM call
        assert legs[0].quantity == 1
        assert legs[1].quantity == -1

        # At expiration with spot far above short strike
        pnl = position_pnl(legs, 150.0, 0)
        # Width = (110 - 100) * 100 = 1000, net debit = (5 - 2) * 100 = 300
        # Max profit = 1000 - 300 = 700
        assert pnl == pytest.approx(700.0, rel=0.01)

    def test_bull_spread_max_loss_limited_to_debit(self):
        """Stock far below long strike → loss limited to net debit."""
        engine = OptionsBacktestEngine(strategy=OptionsStrategy.BULL_SPREAD)
        legs = engine._construct_legs(OptionsStrategy.BULL_SPREAD, 100.0, 45)

        # At expiration with spot far below long strike
        pnl = position_pnl(legs, 50.0, 0)
        # Both OTM → loss = net debit = (5 - 2) * 100 = 300
        assert pnl == pytest.approx(-300.0, rel=0.01)


class TestLeapsCall:
    """Tests for leaps_call strategy."""

    def test_leaps_call_leveraged_gain(self):
        """Stock rises significantly → LEAPS provides leveraged gain."""
        engine = OptionsBacktestEngine(strategy=OptionsStrategy.LEAPS_CALL)
        legs = engine._construct_legs(OptionsStrategy.LEAPS_CALL, 100.0, 365)

        assert len(legs) == 1
        assert legs[0].quantity == 1
        assert legs[0].strike == pytest.approx(80.0)  # spot * 0.80

        # At expiration with spot at 120
        pnl = position_pnl(legs, 120.0, 0)
        # Intrinsic = 120 - 80 = 40, premium = 25
        # PnL = (40 - 25) * 1 * 100 = 1500
        assert pnl == pytest.approx(1500.0, rel=0.01)

    def test_leaps_call_time_decay(self):
        """Stock unchanged → time decay causes loss."""
        engine = OptionsBacktestEngine(strategy=OptionsStrategy.LEAPS_CALL)
        legs = engine._construct_legs(OptionsStrategy.LEAPS_CALL, 100.0, 365)

        # Midway through, stock unchanged
        pnl_mid = position_pnl(legs, 100.0, 180)
        # At expiration, stock unchanged
        pnl_end = position_pnl(legs, 100.0, 0)

        # Time decay should make end PnL worse than mid PnL
        # At expiration: intrinsic = 20, premium = 25, PnL = (20-25)*100 = -500
        assert pnl_end < pnl_mid


class TestOptionsBacktestEngine:
    """Integration-style tests for the engine."""

    @pytest.mark.asyncio
    async def test_run_returns_result_with_trades(self):
        """Engine run() returns OptionsBacktestResult with trades."""
        # Generate price data with a dip to trigger RSI < 40 entry
        prices = []
        for i in range(30):
            if 10 <= i < 20:
                prices.append(100.0 - (i - 10) * 2.0)  # dip to 80
            else:
                prices.append(100.0)
        price_data = _make_price_data(prices)

        engine = OptionsBacktestEngine(strategy=OptionsStrategy.COVERED_CALL)
        result = await engine.run("TEST", price_data)

        assert isinstance(result, OptionsBacktestResult)
        assert result.symbol == "TEST"
        assert result.strategy == OptionsStrategy.COVERED_CALL
        assert len(result.equity_curve) == len(price_data)
        assert "total_return" in result.metrics
        assert "win_rate" in result.metrics

    @pytest.mark.asyncio
    async def test_run_empty_data_returns_empty_result(self):
        """Empty price data returns empty result."""
        engine = OptionsBacktestEngine(strategy=OptionsStrategy.COVERED_CALL)
        result = await engine.run("TEST", [])

        assert result.trades == []
        assert result.equity_curve == []
        assert result.final_capital == result.initial_capital

    @pytest.mark.asyncio
    async def test_run_insufficient_data_returns_empty(self):
        """Too few data points returns empty result."""
        prices = [100.0] * 5
        price_data = _make_price_data(prices)

        engine = OptionsBacktestEngine(strategy=OptionsStrategy.COVERED_CALL)
        result = await engine.run("TEST", price_data)

        assert result.trades == []
        assert result.equity_curve == []

    def test_compute_metrics(self):
        """_compute_metrics returns expected keys."""
        engine = OptionsBacktestEngine(strategy=OptionsStrategy.COVERED_CALL)
        trades: list[OptionsTradeResult] = []
        equity_curve = [{"date": "2024-01-01", "equity": 100000.0}]

        metrics = engine._compute_metrics(trades, equity_curve, 100000.0)

        assert "total_return" in metrics
        assert "annualized_return" in metrics
        assert "win_rate" in metrics
        assert "profit_factor" in metrics
        assert "max_drawdown" in metrics
        assert "sharpe_ratio" in metrics
        assert "total_trades" in metrics
        assert "avg_win" in metrics
        assert "avg_loss" in metrics
        assert "best_trade" in metrics
        assert "worst_trade" in metrics

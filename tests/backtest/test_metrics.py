"""Tests for backtest metrics calculation."""

import pytest

from src.backtest.metrics import (
    calculate_calmar_ratio,
    calculate_max_drawdown_duration,
    calculate_metrics,
    calculate_monthly_returns,
    calculate_performance_report,
    calculate_sortino_ratio,
)
from src.models.backtest import PerformanceReport, PipelineBacktestTrade


class TestCalculateMetrics:
    """Tests for calculate_metrics function."""

    def test_empty_equity_curve(self):
        """Empty equity curve returns zero metrics."""
        metrics = calculate_metrics([], [])
        assert metrics["total_return"] == 0.0
        assert metrics["win_rate"] == 0.0
        assert metrics["sharpe_ratio"] == 0.0

    def test_single_point_equity_curve(self):
        """Single point equity curve returns zero metrics."""
        equity = [{"date": "2024-01-01", "value": 100000.0}]
        metrics = calculate_metrics(equity, [])
        assert metrics["total_return"] == 0.0
        assert metrics["sharpe_ratio"] == 0.0

    def test_total_return_positive(self):
        """Positive total return calculated correctly."""
        equity = [
            {"date": "2024-01-01", "value": 100000.0},
            {"date": "2024-01-02", "value": 110000.0},
        ]
        metrics = calculate_metrics(equity, [])
        assert metrics["total_return"] == pytest.approx(10.0)

    def test_total_return_negative(self):
        """Negative total return calculated correctly."""
        equity = [
            {"date": "2024-01-01", "value": 100000.0},
            {"date": "2024-01-02", "value": 90000.0},
        ]
        metrics = calculate_metrics(equity, [])
        assert metrics["total_return"] == pytest.approx(-10.0)

    def test_win_rate_with_trades(self):
        """Win rate calculated from closed trades."""
        from src.backtest.engine import TradeRecord

        equity = [{"date": "2024-01-01", "value": 100000.0}]
        trades = [
            TradeRecord(
                entry_date="2024-01-01",
                exit_date="2024-01-02",
                entry_price=100.0,
                exit_price=110.0,
                shares=10,
                pnl=100.0,
                pnl_percent=10.0,
                status="closed",
            ),
            TradeRecord(
                entry_date="2024-01-03",
                exit_date="2024-01-04",
                entry_price=110.0,
                exit_price=105.0,
                shares=10,
                pnl=-50.0,
                pnl_percent=-4.55,
                status="closed",
            ),
        ]
        metrics = calculate_metrics(equity, trades)
        assert metrics["win_rate"] == pytest.approx(50.0)
        assert metrics["total_trades"] == 2.0

    def test_profit_factor(self):
        """Profit factor = total wins / total losses."""
        from src.backtest.engine import TradeRecord

        equity = [{"date": "2024-01-01", "value": 100000.0}]
        trades = [
            TradeRecord(
                entry_date="2024-01-01",
                exit_date="2024-01-02",
                entry_price=100.0,
                exit_price=110.0,
                shares=10,
                pnl=100.0,
                pnl_percent=10.0,
                status="closed",
            ),
            TradeRecord(
                entry_date="2024-01-03",
                exit_date="2024-01-04",
                entry_price=110.0,
                exit_price=105.0,
                shares=10,
                pnl=-50.0,
                pnl_percent=-4.55,
                status="closed",
            ),
        ]
        metrics = calculate_metrics(equity, trades)
        assert metrics["profit_factor"] == pytest.approx(2.0)

    def test_max_drawdown(self):
        """Max drawdown detected correctly."""
        equity = [
            {"date": "2024-01-01", "value": 100000.0},
            {"date": "2024-01-02", "value": 110000.0},
            {"date": "2024-01-03", "value": 105000.0},
            {"date": "2024-01-04", "value": 108000.0},
            {"date": "2024-01-05", "value": 95000.0},
            {"date": "2024-01-06", "value": 100000.0},
        ]
        metrics = calculate_metrics(equity, [])
        # Peak at 110000, lowest at 95000 => (110000-95000)/110000 = 0.13636...
        assert metrics["max_drawdown"] == pytest.approx(13.636, rel=0.01)

    def test_sharpe_ratio_zero_std(self):
        """Sharpe ratio is 0 when all returns are identical."""
        equity = [
            {"date": "2024-01-01", "value": 100000.0},
            {"date": "2024-01-02", "value": 100000.0},
            {"date": "2024-01-03", "value": 100000.0},
        ]
        metrics = calculate_metrics(equity, [])
        assert metrics["sharpe_ratio"] == 0.0

    def test_best_worst_trade(self):
        """Best and worst trade tracked correctly."""
        from src.backtest.engine import TradeRecord

        equity = [{"date": "2024-01-01", "value": 100000.0}]
        trades = [
            TradeRecord(
                entry_date="2024-01-01",
                exit_date="2024-01-02",
                entry_price=100.0,
                exit_price=120.0,
                shares=10,
                pnl=200.0,
                pnl_percent=20.0,
                status="closed",
            ),
            TradeRecord(
                entry_date="2024-01-03",
                exit_date="2024-01-04",
                entry_price=120.0,
                exit_price=90.0,
                shares=10,
                pnl=-300.0,
                pnl_percent=-25.0,
                status="closed",
            ),
        ]
        metrics = calculate_metrics(equity, trades)
        assert metrics["best_trade"] == pytest.approx(20.0)
        assert metrics["worst_trade"] == pytest.approx(-25.0)


class TestCalculateMonthlyReturns:
    """Tests for calculate_monthly_returns function."""

    def test_empty_equity_curve(self):
        """Empty input returns empty list."""
        assert calculate_monthly_returns([]) == []

    def test_single_month(self):
        """Single month return calculated."""
        equity = [
            {"date": "2024-01-01", "value": 100000.0},
            {"date": "2024-01-15", "value": 105000.0},
            {"date": "2024-01-31", "value": 103000.0},
        ]
        result = calculate_monthly_returns(equity)
        assert len(result) == 1
        assert result[0]["month"] == "2024-01"
        assert result[0]["return"] == pytest.approx(3.0)

    def test_multiple_months(self):
        """Multiple months with returns."""
        equity = [
            {"date": "2024-01-01", "value": 100000.0},
            {"date": "2024-01-31", "value": 105000.0},
            {"date": "2024-02-01", "value": 105000.0},
            {"date": "2024-02-28", "value": 102000.0},
        ]
        result = calculate_monthly_returns(equity)
        assert len(result) == 2
        assert result[0]["month"] == "2024-01"
        assert result[0]["return"] == pytest.approx(5.0)
        assert result[1]["month"] == "2024-02"
        assert result[1]["return"] == pytest.approx(-2.857, rel=0.01)

    def test_skips_invalid_dates(self):
        """Invalid date formats are skipped gracefully."""
        equity = [
            {"date": "2024-01-01", "value": 100000.0},
            {"date": "bad-date", "value": 105000.0},
            {"date": "2024-02-01", "value": 102000.0},
        ]
        result = calculate_monthly_returns(equity)
        assert len(result) == 2


def _make_equity_curve(values: list[float]) -> list[dict]:
    return [{"date": f"2024-01-{i + 1:02d}", "value": v} for i, v in enumerate(values)]


def _make_trade(entry_price: float, exit_price: float, shares: int = 100) -> PipelineBacktestTrade:
    pnl = (exit_price - entry_price) * shares
    pnl_percent = (pnl / (entry_price * shares)) * 100
    return PipelineBacktestTrade(
        entry_date="2024-01-01", exit_date="2024-01-15",
        entry_price=entry_price, exit_price=exit_price,
        shares=shares, pnl=pnl, pnl_percent=pnl_percent, status="closed",
    )


class TestPerformanceReport:
    """Tests for calculate_performance_report."""

    def test_flat_equity(self):
        curve = _make_equity_curve([100000, 100000, 100000])
        report = calculate_performance_report(curve, [])
        assert isinstance(report, PerformanceReport)
        assert report.total_return == 0.0
        assert report.max_drawdown == 0.0

    def test_profitable_trades(self):
        curve = _make_equity_curve([100000, 101000, 102000])
        trades = [_make_trade(100, 102, 100)]
        report = calculate_performance_report(curve, trades)
        assert report.total_return > 0
        assert report.total_trades == 1
        assert report.win_rate == 100.0

    def test_losing_trades(self):
        curve = _make_equity_curve([100000, 99000, 98000])
        trades = [_make_trade(100, 98, 100)]
        report = calculate_performance_report(curve, trades)
        assert report.total_return < 0
        assert report.total_trades == 1
        assert report.win_rate == 0.0

    def test_mixed_trades(self):
        curve = _make_equity_curve([100000, 101000, 100500])
        trades = [_make_trade(100, 102, 100), _make_trade(100, 98, 100)]
        report = calculate_performance_report(curve, trades)
        assert report.total_trades == 2
        assert report.win_rate == 50.0

    def test_empty_curve(self):
        report = calculate_performance_report([], [])
        assert report.total_return == 0.0
        assert report.total_trades == 0


class TestSortinoRatio:
    """Tests for Sortino ratio."""

    def test_positive_returns(self):
        curve = _make_equity_curve([100000, 100100, 100200, 100300])
        ratio = calculate_sortino_ratio(curve)
        assert ratio > 0

    def test_negative_returns(self):
        curve = _make_equity_curve([100000, 99900, 99800, 99700])
        ratio = calculate_sortino_ratio(curve)
        assert ratio < 0

    def test_short_curve(self):
        ratio = calculate_sortino_ratio(_make_equity_curve([100000]))
        assert ratio == 0.0


class TestCalmarRatio:
    """Tests for Calmar ratio."""

    def test_positive(self):
        assert calculate_calmar_ratio(0.15, 0.10) == pytest.approx(1.5)

    def test_zero_drawdown(self):
        assert calculate_calmar_ratio(0.15, 0.0) == 0.0


class TestMaxDrawdownDuration:
    """Tests for max drawdown duration."""

    def test_no_drawdown(self):
        curve = _make_equity_curve([100, 101, 102, 103])
        assert calculate_max_drawdown_duration(curve) == 0

    def test_with_drawdown(self):
        curve = _make_equity_curve([100, 99, 98, 97, 100, 101])
        assert calculate_max_drawdown_duration(curve) == 3

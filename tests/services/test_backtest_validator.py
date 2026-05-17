"""Tests for BacktestValidator."""

from datetime import date

import pytest
from src.services.backtest_validator import BacktestValidator, BacktestResult


@pytest.fixture
def validator():
    return BacktestValidator()


class TestBacktestValidator:
    def test_hit_profit_target(self, validator):
        result = validator.validate_strategy(
            symbol="NVDA", strategy_type="bull_call",
            entry_date=date(2026, 1, 1), entry_price=130.0,
            target_pct=15.0, stop_loss_pct=10.0,
            historical_prices=[131, 133, 136, 140, 145, 150]
        )
        assert result.hit_profit_target is True
        assert result.final_pnl_pct is not None
        assert result.final_pnl_pct >= 15.0

    def test_hit_stop_loss(self, validator):
        result = validator.validate_strategy(
            symbol="NVDA", strategy_type="bull_call",
            entry_date=date(2026, 1, 1), entry_price=130.0,
            target_pct=20.0, stop_loss_pct=10.0,
            historical_prices=[129, 125, 120, 116, 115]
        )
        assert result.hit_stop_loss is True
        assert result.final_pnl_pct is not None
        assert result.final_pnl_pct <= -10.0

    def test_hold_to_expiry(self, validator):
        result = validator.validate_strategy(
            symbol="NVDA", strategy_type="bull_call",
            entry_date=date(2026, 1, 1), entry_price=130.0,
            target_pct=50.0, stop_loss_pct=30.0,
            historical_prices=[131, 133, 135, 132, 134]
        )
        assert result.hit_profit_target is False
        assert result.hit_stop_loss is False
        assert result.days_held == 5

    def test_batch_validate(self, validator):
        decisions = [
            {"symbol": "NVDA", "strategy_type": "bull_call", "entry_date": date(2026, 1, 1),
             "entry_price": 130.0, "target_pct": 15.0, "stop_loss_pct": 10.0,
             "historical_prices": [131, 133, 136, 140, 145, 150]},
            {"symbol": "AAPL", "strategy_type": "bull_call", "entry_date": date(2026, 1, 1),
             "entry_price": 200.0, "target_pct": 10.0, "stop_loss_pct": 5.0,
             "historical_prices": [202, 205, 210, 215, 220]},
        ]
        results = validator.batch_validate(decisions)
        assert len(results) == 2
        assert results[0].hit_profit_target is True
        assert results[1].hit_profit_target is True

    def test_aggregate_stats(self, validator):
        decisions = [
            {"symbol": "NVDA", "strategy_type": "bull_call", "entry_date": date(2026, 1, 1),
             "entry_price": 130.0, "target_pct": 15.0, "stop_loss_pct": 10.0,
             "historical_prices": [131, 133, 136, 140, 145, 150]},
            {"symbol": "AAPL", "strategy_type": "bull_call", "entry_date": date(2026, 1, 1),
             "entry_price": 200.0, "target_pct": 10.0, "stop_loss_pct": 5.0,
             "historical_prices": [202, 205, 210, 215, 220]},
        ]
        results = validator.batch_validate(decisions)
        stats = validator.aggregate_stats(results)
        assert stats["total_trades"] == 2
        assert stats["win_rate"] == 1.0
        assert stats["avg_pnl_pct"] > 0
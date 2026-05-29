"""Tests for PositionRulesEngine."""

import pytest

from src.agents.position_monitor.rules_engine import PositionRulesEngine, RuleAction


@pytest.fixture
def engine():
    return PositionRulesEngine()


class TestRulesEngine:
    def test_dte_theta_decay_triggers(self, engine):
        results = engine.evaluate(
            position={"symbol": "NVDA", "dte_remaining": 15, "entry_price": 130.0, "current_price": 128.0,
                      "target_pct": 50, "stop_loss_pct": 20, "position_type": "long call"},
            market_data={"price_history_5d": [], "iv_rank": 50}
        )
        actions = [r.action for r in results]
        assert RuleAction.SUGGEST_ROLL in actions

    def test_dte_with_profit_no_trigger(self, engine):
        results = engine.evaluate(
            position={"symbol": "NVDA", "dte_remaining": 15, "entry_price": 130.0, "current_price": 150.0,
                      "target_pct": 50, "stop_loss_pct": 20, "position_type": "long call"},
            market_data={"price_history_5d": [], "iv_rank": 50}
        )
        actions = [r.action for r in results]
        assert RuleAction.SUGGEST_ROLL not in actions

    def test_profit_target_alert(self, engine):
        results = engine.evaluate(
            position={"symbol": "NVDA", "dte_remaining": 30, "entry_price": 130.0, "current_price": 200.0,
                      "target_pct": 50, "stop_loss_pct": 20, "position_type": "long call"},
            market_data={"price_history_5d": [], "iv_rank": 50}
        )
        actions = [r.action for r in results]
        assert RuleAction.ALERT in actions

    def test_stop_loss_alert(self, engine):
        results = engine.evaluate(
            position={"symbol": "NVDA", "dte_remaining": 30, "entry_price": 130.0, "current_price": 100.0,
                      "target_pct": 50, "stop_loss_pct": 20, "position_type": "long call"},
            market_data={"price_history_5d": [], "iv_rank": 50}
        )
        actions = [r.action for r in results]
        assert RuleAction.ALERT in actions
        # stop loss should have highest urgency
        stop_result = [r for r in results if r.rule_name == "stop_loss_triggered"][0]
        assert stop_result.urgency == 5

    def test_consecutive_decline(self, engine):
        results = engine.evaluate(
            position={"symbol": "NVDA", "dte_remaining": 30, "entry_price": 130.0, "current_price": 128.0,
                      "target_pct": 50, "stop_loss_pct": 20, "position_type": "long call"},
            market_data={"price_history_5d": [135, 133, 131, 130, 128], "iv_rank": 50}
        )
        actions = [r.action for r in results]
        assert RuleAction.INCREASE_MONITOR in actions

    def test_high_iv_rank_long_call(self, engine):
        results = engine.evaluate(
            position={"symbol": "NVDA", "dte_remaining": 30, "entry_price": 130.0, "current_price": 135.0,
                      "target_pct": 50, "stop_loss_pct": 20, "position_type": "long call"},
            market_data={"price_history_5d": [], "iv_rank": 85}
        )
        actions = [r.action for r in results]
        assert RuleAction.ALERT in actions

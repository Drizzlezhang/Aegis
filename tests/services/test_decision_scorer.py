"""Tests for DecisionScorer."""

import pytest

from src.services.decision_scorer import DecisionScorer


@pytest.fixture
def scorer():
    return DecisionScorer()


def make_decision(**overrides):
    base = {"id": "test1", "symbol": "NVDA", "entry_price": 130.0, "target_pct": 20, "stop_loss_pct": 10, "strategy_type": "bull_call"}
    base.update(overrides)
    return base


def make_history(**overrides):
    base = {
        "prices_after_entry": [131, 133, 135, 140, 145],
        "exit_price": 145.0,
        "exit_reason": "target_hit",
        "position_size_pct": 5.0,
        "days_held": 30,
        "plan_adherence": "full",
        "was_profitable": True,
    }
    base.update(overrides)
    return base


class TestDecisionScorer:
    def test_perfect_trade_scores_high(self, scorer):
        score = scorer.score(make_decision(), make_history())
        assert score.total_score > 80
        assert "perfect_exit" in score.tags

    def test_poor_timing_low_score(self, scorer):
        score = scorer.score(
            make_decision(entry_price=130.0),
            make_history(prices_after_entry=[130, 125, 120, 100, 90], exit_price=95.0, exit_reason="stop_loss")
        )
        assert score.timing_score <= 10

    def test_exit_target_hit_full_marks(self, scorer):
        score = scorer.score(make_decision(), make_history(exit_reason="target_hit"))
        assert score.exit_score == 30.0

    def test_exit_held_too_long_low_marks(self, scorer):
        score = scorer.score(
            make_decision(entry_price=130.0),
            make_history(
                prices_after_entry=[131, 140, 150, 120, 110],
                exit_price=110.0,
                exit_reason="stop_loss",
                was_profitable=True,
            )
        )
        assert score.exit_score <= 5

    def test_sizing_profit_full_size(self, scorer):
        score = scorer.score(
            make_decision(entry_price=130.0),
            make_history(exit_price=145.0, position_size_pct=5.0)
        )
        assert score.sizing_score == 20.0

    def test_sizing_loss_oversized(self, scorer):
        score = scorer.score(
            make_decision(entry_price=130.0),
            make_history(exit_price=120.0, position_size_pct=10.0)
        )
        assert score.sizing_score == 5.0

    def test_plan_adherence_full(self, scorer):
        score = scorer.score(make_decision(), make_history(plan_adherence="full"))
        assert score.plan_adherence == 20.0

    def test_generate_tags(self, scorer):
        score = scorer.score(
            make_decision(entry_price=130.0),
            make_history(
                prices_after_entry=[131, 133, 135, 140, 145],
                exit_price=145.0,
                exit_reason="target_hit",
                position_size_pct=5.0,
                days_held=30,
                plan_adherence="full",
            )
        )
        assert isinstance(score.tags, list)
        assert "perfect_exit" in score.tags

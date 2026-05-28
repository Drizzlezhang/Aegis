"""Integration tests for PhasePredictor → Debate Agent data flow."""

from datetime import date, datetime

import pytest

from src.agents.debate.judge import InvestmentJudge
from src.agents.debate.phase_evidence import generate_phase_evidence
from src.agents.debate.researchers import BearResearcher, BullResearcher
from src.models.scoring import MacroRegime
from src.models.state import AgentState
from src.models.trend_phase import DimensionScore, TrendPhaseResult, WyckoffPhase


def _make_phase_result(
    phase: WyckoffPhase = WyckoffPhase.MARKUP,
    composite_score: float = 75.0,
    confidence: float = 82.0,
    transition: str | None = "accumulation→markup",
) -> TrendPhaseResult:
    """Build a TrendPhaseResult for testing."""
    dims = [
        DimensionScore(name="trend_momentum", raw_value=80.0, normalized_score=80.0, weight=0.20, weighted_score=16.0),
        DimensionScore(name="velocity", raw_value=70.0, normalized_score=70.0, weight=0.15, weighted_score=10.5),
        DimensionScore(name="acceleration", raw_value=65.0, normalized_score=65.0, weight=0.12, weighted_score=7.8),
        DimensionScore(name="volume", raw_value=75.0, normalized_score=75.0, weight=0.18, weighted_score=13.5),
        DimensionScore(name="mean_reversion", raw_value=55.0, normalized_score=55.0, weight=0.15, weighted_score=8.25),
        DimensionScore(name="macro", raw_value=70.0, normalized_score=70.0, weight=0.10, weighted_score=7.0),
        DimensionScore(name="valuation", raw_value=60.0, normalized_score=60.0, weight=0.10, weighted_score=6.0),
    ]
    return TrendPhaseResult(
        phase=phase,
        composite_score=composite_score,
        dimension_scores=dims,
        confidence=confidence,
        transition=transition,
    )


class TestPhaseDebatePipeline:
    """Integration tests for PhasePredictor → Debate Agent data flow."""

    @pytest.mark.asyncio
    async def test_bullish_phase_enriches_bull_researcher(self):
        """Markup phase evidence should appear in bull researcher context."""
        state = AgentState(symbol="AAPL", trade_date=date.today())
        state.trend_phase_result = _make_phase_result(WyckoffPhase.MARKUP, 75.0, 82.0)

        researcher = BullResearcher()
        arg = await researcher.argue(state)

        # Should contain phase-related evidence
        phase_points = [p for p in arg.key_points if "Wyckoff" in p or "Phase" in p or "趋势动量" in p]
        assert len(phase_points) > 0, f"No phase evidence in bull key_points: {arg.key_points}"

    @pytest.mark.asyncio
    async def test_bearish_phase_enriches_bear_researcher(self):
        """Markdown phase evidence should appear in bear researcher context."""
        state = AgentState(symbol="AAPL", trade_date=date.today())
        dims = [
            DimensionScore(name="trend_momentum", raw_value=25.0, normalized_score=25.0, weight=0.20, weighted_score=5.0),
            DimensionScore(name="velocity", raw_value=30.0, normalized_score=30.0, weight=0.15, weighted_score=4.5),
            DimensionScore(name="acceleration", raw_value=35.0, normalized_score=35.0, weight=0.12, weighted_score=4.2),
            DimensionScore(name="volume", raw_value=20.0, normalized_score=20.0, weight=0.18, weighted_score=3.6),
            DimensionScore(name="mean_reversion", raw_value=40.0, normalized_score=40.0, weight=0.15, weighted_score=6.0),
            DimensionScore(name="macro", raw_value=30.0, normalized_score=30.0, weight=0.10, weighted_score=3.0),
            DimensionScore(name="valuation", raw_value=45.0, normalized_score=45.0, weight=0.10, weighted_score=4.5),
        ]
        state.trend_phase_result = TrendPhaseResult(
            phase=WyckoffPhase.MARKDOWN,
            composite_score=25.0,
            dimension_scores=dims,
            confidence=78.0,
            transition="distribution→markdown",
        )

        researcher = BearResearcher()
        arg = await researcher.argue(state)

        # Should contain bearish phase evidence
        phase_points = [p for p in arg.key_points if "Wyckoff" in p or "Phase" in p or "偏弱" in p]
        assert len(phase_points) > 0, f"No phase evidence in bear key_points: {arg.key_points}"

    @pytest.mark.asyncio
    async def test_no_phase_data_graceful_fallback(self):
        """state.trend_phase_result=None → Debate runs normally without phase injection."""
        state = AgentState(symbol="AAPL", trade_date=date.today())
        state.trend_phase_result = None

        bull = BullResearcher()
        bear = BearResearcher()

        bull_arg = await bull.argue(state)
        bear_arg = await bear.argue(state)

        # Should still produce valid arguments
        assert bull_arg.confidence > 0
        assert bear_arg.confidence > 0
        # No phase-related content
        phase_in_bull = [p for p in bull_arg.key_points if "Wyckoff" in p]
        phase_in_bear = [p for p in bear_arg.key_points if "Wyckoff" in p]
        assert len(phase_in_bull) == 0
        assert len(phase_in_bear) == 0

    def test_low_confidence_no_bonus(self):
        """confidence < 40 → judge gives no bonus."""
        judge = InvestmentJudge()
        state = AgentState(symbol="AAPL", trade_date=date.today())
        state.trend_phase_result = _make_phase_result(WyckoffPhase.MARKUP, 75.0, 30.0)

        bonus = judge._calculate_phase_weight_bonus(state)
        assert bonus == {"bull_bonus": 0.0, "bear_bonus": 0.0}

    def test_high_confidence_bull_bonus(self):
        """confidence > 70 + bullish score → judge gives bull bonus."""
        judge = InvestmentJudge()
        state = AgentState(symbol="AAPL", trade_date=date.today())
        state.trend_phase_result = _make_phase_result(WyckoffPhase.MARKUP, 75.0, 82.0, "accumulation→markup")

        bonus = judge._calculate_phase_weight_bonus(state)
        assert bonus["bull_bonus"] > 0
        assert bonus["bear_bonus"] == 0.0

    def test_no_phase_data_judge_no_bonus(self):
        """No phase data → judge bonus is zero."""
        judge = InvestmentJudge()
        state = AgentState(symbol="AAPL", trade_date=date.today())
        state.trend_phase_result = None

        bonus = judge._calculate_phase_weight_bonus(state)
        assert bonus == {"bull_bonus": 0.0, "bear_bonus": 0.0}

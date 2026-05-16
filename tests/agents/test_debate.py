"""Tests for Bull/Bear debate system."""

import pytest

from src.agents.debate.researchers import BullResearcher, BearResearcher
from src.agents.debate.judge import InvestmentJudge
from src.agents.debate.agent import DebateAgent
from src.models.debate import (
    DebateArgument,
    DebateRole,
    InvestmentRating,
    JudgeVerdict,
)


def make_state(symbol="TEST", analysis_report="", support_levels=None,
               valuation_range=None, recommended_options=None, market_indices=None):
    from src.models import AgentState

    return AgentState(
        symbol=symbol,
        trade_date="2024-01-01",
        analysis_report=analysis_report,
        support_levels=support_levels or [],
        valuation_range=valuation_range,
        recommended_options=recommended_options or [],
        market_indices=market_indices or [],
    )


class TestBullResearcher:
    @pytest.mark.asyncio
    async def test_high_grade_high_confidence(self):
        researcher = BullResearcher()
        state = make_state(analysis_report="Grade: A, Total: 85.0/100\nRegime: risk_on")
        arg = await researcher.argue(state)
        assert arg.role == DebateRole.BULL
        assert arg.position == "bullish"
        assert arg.confidence > 0.55
        assert len(arg.key_points) >= 1

    @pytest.mark.asyncio
    async def test_low_grade_lower_confidence(self):
        researcher = BullResearcher()
        state = make_state(analysis_report="Grade: F, Total: 20.0/100\nRegime: risk_off")
        arg = await researcher.argue(state)
        assert arg.confidence < 0.55
        assert len(arg.risks) > 0

    @pytest.mark.asyncio
    async def test_undervalued_adds_confidence(self):
        researcher = BullResearcher()
        state = make_state(
            analysis_report="Grade: B, Total: 70.0/100\nRegime: risk_on",
        )
        arg = await researcher.argue(state)
        # Without valuation_range, confidence is moderate
        assert arg.confidence >= 0.5

    @pytest.mark.asyncio
    async def test_empty_state_neutral(self):
        researcher = BullResearcher()
        state = make_state()
        arg = await researcher.argue(state)
        assert 0.1 <= arg.confidence <= 1.0
        assert arg.role == DebateRole.BULL


class TestBearResearcher:
    @pytest.mark.asyncio
    async def test_extreme_vix_high_confidence(self):
        researcher = BearResearcher()
        from src.models import MarketIndex

        indices = [
            MarketIndex(
                symbol="^VIX", name="VIX", price=35.0, change=0,
                change_percent=0, timestamp="2024-01-01T00:00:00",
            ),
        ]
        state = make_state(analysis_report="Grade: D, Total: 30.0/100", market_indices=indices)
        arg = await researcher.argue(state)
        assert arg.role == DebateRole.BEAR
        assert arg.position == "bearish"
        assert arg.confidence > 0.55

    @pytest.mark.asyncio
    async def test_risk_off_adds_confidence(self):
        researcher = BearResearcher()
        state = make_state(analysis_report="Grade: C, Total: 55.0/100\nRegime: risk_off")
        arg = await researcher.argue(state)
        assert arg.confidence > 0.55

    @pytest.mark.asyncio
    async def test_empty_state_moderate_confidence(self):
        researcher = BearResearcher()
        state = make_state()
        arg = await researcher.argue(state)
        assert 0.1 <= arg.confidence <= 1.0


class TestInvestmentJudge:
    @pytest.mark.asyncio
    async def test_bull_dominates_strong_buy(self):
        judge = InvestmentJudge()
        bull = DebateArgument(
            role=DebateRole.BULL, position="bullish",
            key_points=["估值便宜", "技术面健康", "支撑位近"],
            confidence=0.9,
        )
        bear = DebateArgument(
            role=DebateRole.BEAR, position="bearish",
            key_points=["VIX偏高"],
            confidence=0.2,
        )
        verdict = await judge.evaluate(bull, bear, "AAPL")
        assert verdict.rating == InvestmentRating.STRONG_BUY
        assert verdict.winning_side == "bull"

    @pytest.mark.asyncio
    async def test_bear_dominates_sell(self):
        judge = InvestmentJudge()
        bull = DebateArgument(
            role=DebateRole.BULL, position="bullish",
            key_points=["技术面中性"],
            confidence=0.3,
        )
        bear = DebateArgument(
            role=DebateRole.BEAR, position="bearish",
            key_points=["系统性风险", "估值过高", "VIX极端"],
            confidence=0.85,
        )
        verdict = await judge.evaluate(bull, bear, "AAPL")
        assert verdict.rating in (InvestmentRating.SELL, InvestmentRating.STRONG_SELL)
        assert verdict.winning_side == "bear"

    @pytest.mark.asyncio
    async def test_close_match_hold(self):
        judge = InvestmentJudge()
        bull = DebateArgument(
            role=DebateRole.BULL, position="bullish",
            key_points=["技术面中性"],
            confidence=0.55,
        )
        bear = DebateArgument(
            role=DebateRole.BEAR, position="bearish",
            key_points=["成交量偏低"],
            confidence=0.50,
        )
        verdict = await judge.evaluate(bull, bear, "AAPL")
        assert verdict.rating == InvestmentRating.HOLD
        assert verdict.winning_side == "neutral"

    @pytest.mark.asyncio
    async def test_buy_signal(self):
        judge = InvestmentJudge()
        bull = DebateArgument(
            role=DebateRole.BULL, position="bullish",
            key_points=["多策略共振", "支撑位明确"],
            confidence=0.7,
        )
        bear = DebateArgument(
            role=DebateRole.BEAR, position="bearish",
            key_points=["波动率偏高"],
            confidence=0.45,
        )
        verdict = await judge.evaluate(bull, bear, "AAPL")
        assert verdict.rating == InvestmentRating.BUY

    @pytest.mark.asyncio
    async def test_positive_keyword_bonus(self):
        judge = InvestmentJudge()
        bull = DebateArgument(
            role=DebateRole.BULL, position="bullish",
            key_points=["估值便宜"],
            confidence=0.5,
        )
        bear = DebateArgument(
            role=DebateRole.BEAR, position="bearish",
            key_points=[],
            confidence=0.45,
        )
        verdict = await judge.evaluate(bull, bear, "AAPL")
        # delta = 0.05 + 0.1 (bonus for 估值便宜) = 0.15 → BUY
        assert verdict.rating == InvestmentRating.BUY


class TestDebateAgent:
    @pytest.mark.asyncio
    async def test_debate_pipeline(self):
        agent = DebateAgent()
        state = make_state(
            analysis_report="Grade: A, Total: 85.0/100\nRegime: risk_on\nRSI: 55.0/10",
        )
        result_state = await agent.run(state)
        assert "## Investment Debate" in result_state.analysis_report
        assert "Verdict:" in result_state.analysis_report
        assert "Winning side:" in result_state.analysis_report
        assert result_state.metadata["debate_result"]["rating"]
        assert result_state.metadata["debate_result"]["bull_confidence"] > 0
        assert result_state.agent_sequence[-1] == "Investment-Debate"
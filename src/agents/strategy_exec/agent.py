"""Strategy-Execution Agent implementation."""

import logging
from typing import Any

from src.agents.base import BaseAgent
from src.config import get_config
from src.models import AgentState
from src.models.debate import JudgeVerdict

from .anti_whipsaw import AntiWhipsaw
from .market_context import analyze_strategy_market_context
from .report import create_action_report
from .strategies import discover_strategies

logger = logging.getLogger(__name__)


class StrategyExecAgent(BaseAgent):
    """Strategy-Execution Agent: Generates options strategy recommendations."""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(
            name="Strategy-Execution",
            description="Generates options strategy recommendations based on support/resistance levels and valuation",
            config=config or {}
        )
        self._config = get_config()
        self._strategies = discover_strategies()
        self._anti_whipsaw = AntiWhipsaw(
            cooldown_hours=self.config.get("whipsaw_cooldown_hours", 24),
            state_file=self.config.get("whipsaw_state_file", "~/.aegis-trader/whipsaw_state.json"),
        )

    async def initialize(self) -> None:
        """Initialize strategy execution resources."""
        pass

    async def run(self, state: AgentState) -> AgentState:
        """Execute strategy generation for the given symbol."""
        symbol = state.symbol.upper()
        logger.info(f"Strategy-Execution starting for symbol: {symbol}")

        if not state.options_chain:
            logger.error(f"No options chain available for {symbol}")
            state.action_report = f"Strategy-Execution Error: No options chain available for {symbol}"
            state.strategy_result = state.snapshot_strategy()
            state.add_agent_step(self.name)
            return state

        support_levels = state.support_levels
        resistance_levels = state.resistance_levels
        valuation_range = state.valuation_range
        current_price = state.options_chain.spot_price
        debate_verdict = self._extract_debate_verdict(state)

        if debate_verdict is not None and self._is_bearish_verdict(debate_verdict):
            state.recommended_options = []
            state.action_report = (
                state.action_report
                + f"\n\n## Strategy Skipped\nDebate verdict: {debate_verdict.rating.value} — no entry strategies evaluated."
            )
            state.strategy_result = state.snapshot_strategy()
            state.add_agent_step(self.name)
            return state

        market_context = analyze_strategy_market_context(state.market_indices)
        if market_context.vix_level is not None:
            logger.info(
                f"Strategy context for {symbol}: VIX={market_context.vix_level:.2f}, "
                f"sentiment={market_context.market_sentiment}, regime={market_context.volatility_regime}, "
                f"sizing={market_context.position_size_factor:.0%}"
            )

        recommendations = []
        for strategy in self._strategies:
            recommendation = strategy.generate(
                symbol=symbol,
                options_chain=state.options_chain,
                support_levels=support_levels,
                resistance_levels=resistance_levels,
                valuation_range=valuation_range,
                current_price=current_price,
                market_context=market_context,
            )
            if recommendation:
                recommendations.append(recommendation)

        decision_direction = self._determine_direction(debate_verdict, recommendations)
        allowed, whipsaw_reason = self._anti_whipsaw.should_allow(symbol, decision_direction)
        if not allowed:
            state.recommended_options = []
            state.action_report = (
                state.action_report
                + f"\n\n## Anti-Whipsaw Blocked\n{symbol}: {whipsaw_reason}."
            )
            state.strategy_result = state.snapshot_strategy()
            state.add_agent_step(self.name)
            return state

        state.recommended_options = recommendations
        state.action_report = create_action_report(
            symbol=symbol,
            recommendations=recommendations,
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            valuation_range=valuation_range,
            market_context=market_context,
        )
        state.strategy_result = state.snapshot_strategy()
        if recommendations:
            self._anti_whipsaw.record_decision(symbol, decision_direction)

        state.add_agent_step(self.name)
        logger.info(f"Strategy-Execution completed for {symbol}, generated {len(recommendations)} recommendations")
        return state

    def _extract_debate_verdict(self, state: AgentState) -> JudgeVerdict | None:
        debate_data = state.metadata.get("debate_result")
        if not debate_data:
            return None
        if isinstance(debate_data, JudgeVerdict):
            return debate_data
        if isinstance(debate_data, dict):
            try:
                return JudgeVerdict(**debate_data)
            except (TypeError, ValueError):
                logger.warning("Malformed debate_result metadata, ignoring verdict")
        return None

    @staticmethod
    def _is_bearish_verdict(verdict: JudgeVerdict | None) -> bool:
        return verdict is not None and verdict.rating.value in ("sell", "strong_sell")

    @staticmethod
    def _determine_direction(verdict: JudgeVerdict | None, recommendations: list) -> str:
        if verdict is not None and verdict.rating.value in ("sell", "strong_sell"):
            return "bearish"
        if recommendations:
            return "bullish"
        return "neutral"

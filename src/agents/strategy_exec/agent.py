"""Strategy-Execution Agent implementation."""

import logging
from typing import Any

from src.agents.base import BaseAgent
from src.config import get_config
from src.models import AgentState
from src.models.debate import JudgeVerdict
from src.models.paper import OrderSide, OrderType

from .anti_whipsaw import AntiWhipsaw
from .brokers.base import BrokerBase
from .brokers.paper import PaperBroker
from .market_context import adjust_position_for_phase, analyze_strategy_market_context
from .report import create_action_report
from .strategies import discover_strategies

logger = logging.getLogger(__name__)


class StrategyExecAgent(BaseAgent):
    """Strategy-Execution Agent: Generates options strategy recommendations."""

    def __init__(self, config: dict[str, Any] | None = None, broker: BrokerBase | None = None):
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
        self._execution_mode = self._config.agent.execution_mode
        self._broker = broker
        if self._broker is None and self._execution_mode == "paper":
            self._broker = PaperBroker()

    async def initialize(self) -> None:
        """Initialize strategy execution resources."""
        pass

    async def execute_signal(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        limit_price: float | None = None,
    ) -> str | None:
        """Execute a trading signal through the broker.

        Args:
            symbol: Trading symbol.
            side: Buy or sell.
            quantity: Number of shares/contracts.
            order_type: Market, limit, or stop.
            limit_price: Required for limit orders.

        Returns:
            Order ID if execution mode is paper/live, None if disabled.
        """
        if self._execution_mode == "disabled" or self._broker is None:
            logger.debug("Execution disabled, skipping signal for %s", symbol)
            return None

        result = await self._broker.place_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
        )
        if result.success:
            logger.info(
                "Signal executed: %s %s %d %s → %s",
                symbol, side.value, quantity, order_type.value, result.order_id,
            )
            return result.order_id
        logger.warning("Signal execution failed: %s", result.message)
        return None

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

        # Phase-aware position sizing
        if state.trend_phase_result:
            from src.agents.debate.phase_evidence import generate_phase_evidence
            pe = generate_phase_evidence(state.trend_phase_result)
            phase_adjusted = adjust_position_for_phase(market_context.position_size_factor, pe)
            logger.info(
                f"Phase position adjustment: bias={pe.position_bias}, "
                f"confidence={pe.confidence:.0f}, "
                f"factor={market_context.position_size_factor:.2f}→{phase_adjusted:.2f}"
            )
            market_context.position_size_factor = phase_adjusted

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

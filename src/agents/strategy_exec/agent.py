"""Strategy-Execution Agent implementation."""

import logging
from typing import Any

from src.agents.base import BaseAgent
from src.config import get_config
from src.models import AgentState

from .report import create_action_report
from .strategies import (
    generate_bull_spread_strategy,
    generate_covered_call_strategy,
    generate_leaps_call_strategy,
)

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
            state.add_agent_step(self.name)
            return state

        support_levels = state.support_levels
        resistance_levels = state.resistance_levels
        valuation_range = state.valuation_range
        current_price = state.options_chain.spot_price

        entry_support = None
        if support_levels:
            entry_support = max(support_levels, key=lambda x: x.confidence)

        recommendations = []

        leaps_rec = generate_leaps_call_strategy(symbol, state.options_chain, entry_support, valuation_range, current_price)
        if leaps_rec:
            recommendations.append(leaps_rec)

        if entry_support:
            bull_spread_rec = generate_bull_spread_strategy(symbol, state.options_chain, entry_support, current_price)
            if bull_spread_rec:
                recommendations.append(bull_spread_rec)

        covered_call_rec = generate_covered_call_strategy(symbol, state.options_chain, resistance_levels, current_price)
        if covered_call_rec:
            recommendations.append(covered_call_rec)

        state.recommended_options = recommendations
        state.action_report = create_action_report(
            symbol=symbol,
            recommendations=recommendations,
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            valuation_range=valuation_range
        )

        state.add_agent_step(self.name)
        logger.info(f"Strategy-Execution completed for {symbol}, generated {len(recommendations)} recommendations")
        return state

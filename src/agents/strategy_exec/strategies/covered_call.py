"""Covered call strategy plugin."""

from __future__ import annotations

import logging
from typing import Any

from src.models import RecommendedOption, SupportResistanceLevel

from ..market_context import StrategyMarketContext
from .base import StrategyGenerator

logger = logging.getLogger(__name__)


class CoveredCallStrategy(StrategyGenerator):
    name = "covered_call"

    def generate(
        self,
        symbol: str,
        options_chain: Any,
        support_levels: list[SupportResistanceLevel],
        resistance_levels: list[SupportResistanceLevel],
        valuation_range: Any | None,
        current_price: float,
        market_context: StrategyMarketContext | None = None,
    ) -> RecommendedOption | None:
        try:
            target_strike = None
            if resistance_levels:
                nearest_resistance = min(resistance_levels, key=lambda level: level.price)
                target_strike = nearest_resistance.price
            if not target_strike:
                target_strike = current_price * 1.08

            suitable_calls = [
                c for c in options_chain.calls
                if c.is_leaps and abs(c.strike - target_strike) / target_strike < 0.05
            ]
            if not suitable_calls:
                return None

            best_call = min(suitable_calls, key=lambda c: abs(c.strike - target_strike))
            premium = best_call.mid_price or best_call.last_price or 0.0
            if premium <= 0:
                return None

            annual_yield = (premium / current_price) * (365 / max(best_call.days_to_expiry, 30)) * 100
            confidence = 0.5
            if resistance_levels:
                nearest_resistance = min(resistance_levels, key=lambda level: level.price)
                confidence += nearest_resistance.confidence * 0.2
            if market_context:
                confidence += market_context.covered_call_confidence_delta
                confidence = max(0.1, min(1.0, confidence))

            reasoning = f"Covered Call strategy for {symbol} (existing stock position):\n"
            reasoning += f"  • Sell Call: Strike {best_call.strike:.2f}, Premium {premium:.2f}\n"
            reasoning += f"  • Annual Yield: {annual_yield:.1f}%\n"
            if market_context and market_context.market_sentiment == "bearish":
                reasoning += "  • Bearish macro — income generation prioritized over upside capture\n"
            reasoning += f"  • If stock stays below {best_call.strike:.2f}, keep full premium\n"
            reasoning += f"  • If stock rises above {best_call.strike:.2f}, shares called away at profit"

            return RecommendedOption(
                contract=best_call,
                recommendation_type=self.name,
                entry_price=-premium,
                target_price=premium,
                stop_loss=None,
                risk_reward_ratio=None,
                confidence=confidence,
                reasoning=reasoning,
            )
        except Exception as e:
            logger.error(f"Error generating Covered Call strategy for {symbol}: {e}")
            return None

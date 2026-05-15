"""Bull spread strategy plugin."""

from __future__ import annotations

import logging
from typing import Any

from src.models import RecommendedOption, SupportResistanceLevel

from ..market_context import StrategyMarketContext
from .base import StrategyGenerator

logger = logging.getLogger(__name__)


class BullSpreadStrategy(StrategyGenerator):
    name = "bull_spread"

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
            entry_support = max(support_levels, key=lambda level: level.confidence) if support_levels else None
            if not entry_support:
                return None

            leaps_calls = [c for c in options_chain.calls if c.is_leaps]
            if len(leaps_calls) < 2:
                return None

            leaps_calls.sort(key=lambda c: c.strike)
            lower_strike = None
            for call in leaps_calls:
                if call.strike <= current_price * 1.02:
                    lower_strike = call
            if not lower_strike:
                lower_strike = leaps_calls[0]

            higher_strike = None
            for call in reversed(leaps_calls):
                if call.strike > lower_strike.strike and call.strike <= current_price * 1.15:
                    higher_strike = call
                    break
            if not higher_strike:
                return None

            lower_premium = lower_strike.mid_price or lower_strike.last_price or 0.0
            higher_premium = higher_strike.mid_price or higher_strike.last_price or 0.0
            spread_cost = lower_premium - higher_premium
            if spread_cost <= 0:
                return None

            max_profit = (higher_strike.strike - lower_strike.strike) - spread_cost
            max_loss = spread_cost
            risk_reward_ratio = max_profit / max_loss if max_loss > 0 else None

            confidence = 0.5 + (entry_support.confidence * 0.3)
            if market_context:
                confidence += market_context.bull_spread_confidence_delta
                confidence = max(0.1, min(1.0, confidence))

            reasoning = f"Bull Spread strategy for {symbol}:\n"
            reasoning += f"  • Buy Call: Strike {lower_strike.strike:.2f}, Premium {lower_premium:.2f}\n"
            reasoning += f"  • Sell Call: Strike {higher_strike.strike:.2f}, Premium {higher_premium:.2f}\n"
            reasoning += f"  • Net Debit: {spread_cost:.2f}\n"
            reasoning += f"  • Max Profit: {max_profit:.2f}\n"
            reasoning += f"  • Max Loss: {max_loss:.2f}\n"
            if risk_reward_ratio:
                reasoning += f"  • Risk/Reward: {risk_reward_ratio:.2f}\n"
            if market_context and market_context.volatility_regime != "normal":
                reasoning += f"  • Macro: VIX {market_context.vix_level:.2f} ({market_context.volatility_regime}) — defined risk preferred\n"
            reasoning += f"  • Breakeven: {lower_strike.strike + spread_cost:.2f}"

            return RecommendedOption(
                contract=lower_strike,
                recommendation_type=self.name,
                entry_price=spread_cost,
                target_price=max_profit,
                stop_loss=spread_cost * 0.5,
                risk_reward_ratio=risk_reward_ratio,
                confidence=confidence,
                reasoning=reasoning,
                support_levels=[entry_support],
            )
        except Exception as e:
            logger.error(f"Error generating Bull Spread strategy for {symbol}: {e}")
            return None

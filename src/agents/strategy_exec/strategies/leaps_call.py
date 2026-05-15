"""LEAPS call strategy plugin."""

from __future__ import annotations

import logging
from typing import Any

from src.models import RecommendedOption, SupportResistanceLevel

from ..market_context import StrategyMarketContext, should_skip_leaps_for_tech
from .base import StrategyGenerator

logger = logging.getLogger(__name__)


class LeapsCallStrategy(StrategyGenerator):
    name = "leaps_call"

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
            if market_context and not market_context.leaps_call_enabled:
                logger.info(f"LEAPS Call disabled for {symbol} due to high VIX ({market_context.vix_level:.2f})")
                return None

            if market_context and should_skip_leaps_for_tech(symbol, market_context):
                logger.info(f"LEAPS Call skipped for tech stock {symbol} during NDX weakness")
                return None

            leaps_calls = [
                c for c in options_chain.calls
                if c.is_leaps and c.delta and 0.6 <= c.delta <= 0.8
            ]
            if not leaps_calls:
                logger.warning(f"No suitable LEAPS Call options found for {symbol}")
                return None

            leaps_calls.sort(key=lambda c: abs(c.delta - 0.7) if c.delta else float("inf"))
            best_call = leaps_calls[0]
            entry_price = best_call.mid_price or best_call.last_price or 0.0
            if entry_price <= 0:
                return None

            entry_support = max(support_levels, key=lambda level: level.confidence) if support_levels else None
            target_price = None
            if entry_support:
                target_price = entry_price * 2.0
            elif valuation_range and valuation_range.fair_estimate > current_price:
                target_price = entry_price * 1.5

            stop_loss = entry_price * 0.5 if entry_price > 0 else None
            risk_reward_ratio = None
            if target_price and stop_loss:
                potential_gain = target_price - entry_price
                max_loss = entry_price - stop_loss
                if max_loss > 0:
                    risk_reward_ratio = potential_gain / max_loss

            confidence = 0.6
            if entry_support:
                confidence += entry_support.confidence * 0.3
            if valuation_range and valuation_range.is_undervalued:
                confidence += 0.1
            if market_context:
                confidence += market_context.leaps_confidence_delta
                confidence = max(0.1, min(1.0, confidence))

            reasoning = f"LEAPS Call strategy for {symbol}:\n"
            reasoning += f"  • Strike: {best_call.strike:.2f}, Expiry: {best_call.expiry}\n"
            reasoning += f"  • Delta: {best_call.delta:.2f} (within target range 0.6-0.8)\n"
            if entry_support:
                reasoning += f"  • Entry near support: {entry_support.price:.2f}\n"
            if valuation_range:
                reasoning += f"  • Valuation: {valuation_range.discount_to_fair:.1f}% discount to fair\n"
            if market_context and market_context.volatility_regime != "normal":
                reasoning += f"  • Macro context: VIX {market_context.vix_level:.2f} ({market_context.volatility_regime})\n"
            reasoning += f"  • Risk/Reward: {risk_reward_ratio:.2f}" if risk_reward_ratio else ""

            return RecommendedOption(
                contract=best_call,
                recommendation_type=self.name,
                entry_price=entry_price,
                target_price=target_price,
                stop_loss=stop_loss,
                risk_reward_ratio=risk_reward_ratio,
                confidence=confidence,
                reasoning=reasoning,
                support_levels=[entry_support] if entry_support else [],
            )
        except Exception as e:
            logger.error(f"Error generating LEAPS Call strategy for {symbol}: {e}")
            return None

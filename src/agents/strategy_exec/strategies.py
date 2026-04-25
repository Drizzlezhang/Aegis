"""Strategy generation logic for Strategy-Execution Agent."""

import logging
from typing import Any

from src.models import RecommendedOption, SupportResistanceLevel

from .market_context import StrategyMarketContext, should_skip_leaps_for_tech

logger = logging.getLogger(__name__)


def generate_leaps_call_strategy(
    symbol: str,
    options_chain: Any,
    entry_support: SupportResistanceLevel | None,
    valuation_range: Any | None,
    current_price: float,
    market_context: StrategyMarketContext | None = None,
) -> RecommendedOption | None:
    """Generate LEAPS Call strategy recommendation."""
    try:
        # Macro guardrails
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

        leaps_calls.sort(key=lambda c: abs(c.delta - 0.7) if c.delta else float('inf'))
        best_call = leaps_calls[0]

        entry_price = best_call.mid_price or best_call.last_price or 0.0
        if entry_price <= 0:
            return None

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

        # Apply macro adjustments
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
            recommendation_type="leaps_call",
            entry_price=entry_price,
            target_price=target_price,
            stop_loss=stop_loss,
            risk_reward_ratio=risk_reward_ratio,
            confidence=confidence,
            reasoning=reasoning,
            support_levels=[entry_support] if entry_support else []
        )

    except Exception as e:
        logger.error(f"Error generating LEAPS Call strategy for {symbol}: {e}")
        return None


def generate_bull_spread_strategy(
    symbol: str,
    options_chain: Any,
    entry_support: SupportResistanceLevel,
    current_price: float,
    market_context: StrategyMarketContext | None = None,
) -> RecommendedOption | None:
    """Generate Bull Spread strategy recommendation."""
    try:
        leaps_calls = [c for c in options_chain.calls if c.is_leaps]
        if len(leaps_calls) < 2:
            return None

        leaps_calls.sort(key=lambda c: c.strike)

        lower_strike = None
        for call in leaps_calls:
            if call.strike <= current_price * 1.02:
                lower_strike = call
                break
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

        # Apply macro adjustments
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
            recommendation_type="bull_spread",
            entry_price=spread_cost,
            target_price=max_profit,
            stop_loss=spread_cost * 0.5,
            risk_reward_ratio=risk_reward_ratio,
            confidence=confidence,
            reasoning=reasoning,
            support_levels=[entry_support]
        )

    except Exception as e:
        logger.error(f"Error generating Bull Spread strategy for {symbol}: {e}")
        return None


def generate_covered_call_strategy(
    symbol: str,
    options_chain: Any,
    resistance_levels: list[SupportResistanceLevel],
    current_price: float,
    market_context: StrategyMarketContext | None = None,
) -> RecommendedOption | None:
    """Generate Covered Call strategy recommendation."""
    try:
        target_strike = None
        if resistance_levels:
            nearest_resistance = min(resistance_levels, key=lambda x: x.price)
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
            nearest_resistance = min(resistance_levels, key=lambda x: x.price)
            confidence += nearest_resistance.confidence * 0.2

        # Apply macro adjustments
        if market_context:
            confidence += market_context.covered_call_confidence_delta
            confidence = max(0.1, min(1.0, confidence))

        reasoning = f"Covered Call strategy for {symbol} (existing stock position):\n"
        reasoning += f"  • Sell Call: Strike {best_call.strike:.2f}, Premium {premium:.2f}\n"
        reasoning += f"  • Annual Yield: {annual_yield:.1f}%\n"
        if market_context and market_context.market_sentiment == "bearish":
            reasoning += f"  • Bearish macro — income generation prioritized over upside capture\n"
        reasoning += f"  • If stock stays below {best_call.strike:.2f}, keep full premium\n"
        reasoning += f"  • If stock rises above {best_call.strike:.2f}, shares called away at profit"

        return RecommendedOption(
            contract=best_call,
            recommendation_type="covered_call",
            entry_price=-premium,
            target_price=premium,
            stop_loss=None,
            risk_reward_ratio=None,
            confidence=confidence,
            reasoning=reasoning
        )

    except Exception as e:
        logger.error(f"Error generating Covered Call strategy for {symbol}: {e}")
        return None

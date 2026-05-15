"""Strategy discovery, plugins, and compatibility exports."""

from typing import Any

from src.models import RecommendedOption, SupportResistanceLevel

from ..market_context import StrategyMarketContext
from .base import StrategyGenerator, discover_strategies
from .bull_spread import BullSpreadStrategy
from .covered_call import CoveredCallStrategy
from .leaps_call import LeapsCallStrategy


def generate_leaps_call_strategy(
    symbol: str,
    options_chain: Any,
    entry_support: SupportResistanceLevel | None,
    valuation_range: Any | None,
    current_price: float,
    market_context: StrategyMarketContext | None = None,
) -> RecommendedOption | None:
    return LeapsCallStrategy().generate(
        symbol=symbol,
        options_chain=options_chain,
        support_levels=[entry_support] if entry_support else [],
        resistance_levels=[],
        valuation_range=valuation_range,
        current_price=current_price,
        market_context=market_context,
    )


def generate_bull_spread_strategy(
    symbol: str,
    options_chain: Any,
    entry_support: SupportResistanceLevel,
    current_price: float,
    market_context: StrategyMarketContext | None = None,
) -> RecommendedOption | None:
    return BullSpreadStrategy().generate(
        symbol=symbol,
        options_chain=options_chain,
        support_levels=[entry_support],
        resistance_levels=[],
        valuation_range=None,
        current_price=current_price,
        market_context=market_context,
    )


def generate_covered_call_strategy(
    symbol: str,
    options_chain: Any,
    resistance_levels: list[SupportResistanceLevel],
    current_price: float,
    market_context: StrategyMarketContext | None = None,
) -> RecommendedOption | None:
    return CoveredCallStrategy().generate(
        symbol=symbol,
        options_chain=options_chain,
        support_levels=[],
        resistance_levels=resistance_levels,
        valuation_range=None,
        current_price=current_price,
        market_context=market_context,
    )


__all__ = [
    "StrategyGenerator",
    "BullSpreadStrategy",
    "CoveredCallStrategy",
    "LeapsCallStrategy",
    "discover_strategies",
    "generate_leaps_call_strategy",
    "generate_bull_spread_strategy",
    "generate_covered_call_strategy",
]

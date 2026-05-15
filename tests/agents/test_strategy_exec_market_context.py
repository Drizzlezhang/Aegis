"""Tests for Strategy-Execution market context integration."""

from datetime import date, datetime
from types import SimpleNamespace

import pytest

from src.agents.strategy_exec.market_context import (
    StrategyMarketContext,
    analyze_strategy_market_context,
    format_strategy_market_summary,
    should_skip_leaps_for_tech,
)
from src.agents.strategy_exec.strategies import BaseStrategy, LeapsCallStrategy, discover_strategies
from src.agents.strategy_exec.strategies.base import StrategyGenerator
from src.agents.strategy_exec.strategies.bull_spread import BullSpreadStrategy
from src.models import MarketIndex, SupportResistanceLevel
from src.models.options import OptionContract, OptionType


def make_index(symbol: str, price: float, change_pct: float) -> MarketIndex:
    return MarketIndex(
        symbol=symbol,
        name=symbol,
        price=price,
        change=price * change_pct / 100,
        change_percent=change_pct,
        timestamp=datetime(2024, 1, 1),
    )


def make_call(strike: float, last_price: float) -> OptionContract:
    return OptionContract(
        symbol=f"QQQ-{strike}",
        underlying="QQQ",
        contract_symbol=f"QQQ260101C{int(strike * 1000):08d}",
        strike=strike,
        expiry=date(2028, 1, 21),
        option_type=OptionType.CALL,
        last_price=last_price,
        bid=last_price,
        ask=last_price,
    )


class TestAnalyzeStrategyMarketContext:
    def test_empty_indices(self):
        ctx = analyze_strategy_market_context([])
        assert ctx.vix_level is None
        assert ctx.leaps_call_enabled is True
        assert ctx.position_size_factor == 1.0

    def test_vix_low(self):
        ctx = analyze_strategy_market_context([make_index("^VIX", 12.0, 0.0)])
        assert ctx.volatility_regime == "low"
        assert ctx.leaps_confidence_delta == 0.05
        assert ctx.covered_call_confidence_delta == -0.05
        assert ctx.leaps_call_enabled is True

    def test_vix_elevated(self):
        ctx = analyze_strategy_market_context([make_index("^VIX", 27.0, 0.0)])
        assert ctx.volatility_regime == "elevated"
        assert ctx.leaps_confidence_delta == -0.15
        assert ctx.bull_spread_confidence_delta == 0.1
        assert ctx.position_size_factor == 0.8
        assert "defined-risk" in ctx.risk_warning

    def test_vix_high_disables_leaps(self):
        ctx = analyze_strategy_market_context([make_index("^VIX", 35.0, 0.0)])
        assert ctx.volatility_regime == "high"
        assert ctx.leaps_call_enabled is False
        assert ctx.leaps_confidence_delta == -0.3
        assert ctx.bull_spread_confidence_delta == 0.15
        assert ctx.covered_call_confidence_delta == 0.1
        assert ctx.position_size_factor == 0.5

    def test_bullish_sentiment_boosts_leaps(self):
        ctx = analyze_strategy_market_context([
            make_index("^VIX", 20.0, 0.0),
            make_index("^GSPC", 4500.0, 1.5),
        ])
        assert ctx.market_sentiment == "bullish"
        assert ctx.leaps_confidence_delta == 0.05

    def test_bearish_sentiment_reduces_leaps_boosts_cc(self):
        ctx = analyze_strategy_market_context([
            make_index("^VIX", 20.0, 0.0),
            make_index("^GSPC", 4500.0, -1.5),
        ])
        assert ctx.market_sentiment == "bearish"
        assert ctx.leaps_confidence_delta == -0.1
        assert ctx.covered_call_confidence_delta == 0.1

    def test_combined_vix_and_bearish(self):
        # Elevated VIX (-0.15) + bearish (-0.1) = -0.25 for leaps
        ctx = analyze_strategy_market_context([
            make_index("^VIX", 28.0, 0.0),
            make_index("^GSPC", 4500.0, -1.5),
        ])
        assert ctx.leaps_confidence_delta == -0.25
        assert ctx.bull_spread_confidence_delta == 0.1

    def test_ndx_tech_caution(self):
        ctx = analyze_strategy_market_context([make_index("^IXIC", 14000.0, -2.5)])
        assert ctx.tech_caution is True
        assert ctx.leaps_confidence_delta == -0.1
        assert "tech" in ctx.risk_warning

    def test_ndx_tech_caution_with_vix(self):
        # VIX normal (0.0) + NDX drop (-0.1) = -0.1
        ctx = analyze_strategy_market_context([
            make_index("^VIX", 20.0, 0.0),
            make_index("^IXIC", 14000.0, -2.5),
        ])
        assert ctx.tech_caution is True
        assert ctx.leaps_confidence_delta == -0.1


class TestShouldSkipLeapsForTech:
    def test_tech_stock_during_weakness(self):
        ctx = StrategyMarketContext(tech_caution=True)
        assert should_skip_leaps_for_tech("NVDA", ctx) is True
        assert should_skip_leaps_for_tech("AAPL", ctx) is True
        assert should_skip_leaps_for_tech("QQQ", ctx) is True

    def test_non_tech_stock(self):
        ctx = StrategyMarketContext(tech_caution=True)
        assert should_skip_leaps_for_tech("KO", ctx) is False
        assert should_skip_leaps_for_tech("SPY", ctx) is False

    def test_no_tech_caution(self):
        ctx = StrategyMarketContext(tech_caution=False)
        assert should_skip_leaps_for_tech("NVDA", ctx) is False

    def test_case_insensitive(self):
        ctx = StrategyMarketContext(tech_caution=True)
        assert should_skip_leaps_for_tech("nvda", ctx) is True
        assert should_skip_leaps_for_tech("NvDa", ctx) is True


class TestStrategyExports:
    def test_discover_strategies_returns_five_plugins(self):
        strategies = discover_strategies()

        assert len(strategies) == 5
        assert {strategy.name for strategy in strategies} == {
            "leaps_call",
            "bull_spread",
            "covered_call",
            "left_side_leaps",
            "right_side_leaps",
        }

    def test_base_strategy_alias_matches_strategy_generator(self):
        assert BaseStrategy is StrategyGenerator

    def test_lazy_compat_export_keeps_legacy_class_import(self):
        assert LeapsCallStrategy.__name__ == "LeapsCallStrategy"


class TestBullSpreadStrategy:
    def test_bull_spread_selects_highest_strike_within_threshold(self):
        strategy = BullSpreadStrategy()
        options_chain = SimpleNamespace(
            calls=[
                make_call(90.0, 14.0),
                make_call(95.0, 10.5),
                make_call(100.0, 7.5),
                make_call(105.0, 5.0),
                make_call(110.0, 3.0),
            ]
        )
        support_levels = [
            SupportResistanceLevel(
                price=98.0,
                level_type="support",
                source="volume_profile",
                confidence=0.9,
            )
        ]

        recommendation = strategy.generate(
            symbol="QQQ",
            options_chain=options_chain,
            support_levels=support_levels,
            resistance_levels=[],
            valuation_range=None,
            current_price=100.0,
        )

        assert recommendation is not None
        assert recommendation.contract.strike == 100.0
        assert recommendation.entry_price == 4.5


class TestFormatStrategyMarketSummary:
    def test_full_summary(self):
        ctx = StrategyMarketContext(
            vix_level=28.0,
            spx_change_pct=-1.5,
            ndx_change_pct=-2.5,
            market_sentiment="bearish",
            volatility_regime="elevated",
            leaps_call_enabled=True,
            leaps_confidence_delta=-0.25,
            bull_spread_confidence_delta=0.1,
            covered_call_confidence_delta=0.1,
            position_size_factor=0.8,
            risk_warning="Reduce position size",
            tech_caution=True,
        )
        summary = format_strategy_market_summary(ctx)
        assert "VIX: 28.00" in summary
        assert "bearish" in summary
        assert "80%" in summary
        assert "LEAPS Call: -25%" in summary
        assert "Bull Spread: +10%" in summary
        assert "Covered Call: +10%" in summary
        assert "Tech stocks: extra caution" in summary
        assert "Reduce position size" in summary

    def test_leaps_disabled(self):
        ctx = StrategyMarketContext(
            vix_level=35.0,
            leaps_call_enabled=False,
        )
        summary = format_strategy_market_summary(ctx)
        assert "DISABLED" in summary

    def test_partial_context(self):
        ctx = StrategyMarketContext(vix_level=15.0)
        summary = format_strategy_market_summary(ctx)
        assert "VIX: 15.00" in summary
        assert "SPX" not in summary

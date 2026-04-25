"""Tests for Quant-Brain market context integration."""

import pytest

from src.agents.quant_brain.market_context import (
    MarketContext,
    adjust_confidence_for_market,
    analyze_market_context,
    format_market_summary,
)
from src.models import MarketIndex


def make_index(symbol: str, price: float, change_pct: float) -> MarketIndex:
    return MarketIndex(
        symbol=symbol,
        name=symbol,
        price=price,
        change=price * change_pct / 100,
        change_percent=change_pct,
        timestamp="2024-01-01T00:00:00",
    )


class TestAnalyzeMarketContext:
    def test_empty_indices(self):
        ctx = analyze_market_context([])
        assert ctx.vix_level is None
        assert ctx.spx_change_pct is None
        assert ctx.ndx_change_pct is None
        assert ctx.market_sentiment == "neutral"
        assert ctx.volatility_regime == "normal"

    def test_vix_low(self):
        indices = [make_index("^VIX", 12.0, 0.0)]
        ctx = analyze_market_context(indices)
        assert ctx.vix_level == 12.0
        assert ctx.volatility_regime == "low"
        assert ctx.confidence_adjustment == 0.05
        assert ctx.position_size_factor == 1.0

    def test_vix_normal(self):
        indices = [make_index("^VIX", 20.0, 0.0)]
        ctx = analyze_market_context(indices)
        assert ctx.vix_level == 20.0
        assert ctx.volatility_regime == "normal"
        assert ctx.confidence_adjustment == 0.0

    def test_vix_elevated(self):
        indices = [make_index("^VIX", 27.0, 0.0)]
        ctx = analyze_market_context(indices)
        assert ctx.vix_level == 27.0
        assert ctx.volatility_regime == "elevated"
        assert ctx.confidence_adjustment == -0.08
        assert ctx.position_size_factor == 0.8
        assert "reduce position size" in ctx.risk_warning

    def test_vix_high(self):
        indices = [make_index("^VIX", 35.0, 0.0)]
        ctx = analyze_market_context(indices)
        assert ctx.vix_level == 35.0
        assert ctx.volatility_regime == "high"
        assert ctx.confidence_adjustment == -0.15
        assert ctx.position_size_factor == 0.5
        assert "avoid new positions" in ctx.risk_warning

    def test_spx_bullish(self):
        indices = [make_index("^GSPC", 4500.0, 1.5)]
        ctx = analyze_market_context(indices)
        assert ctx.spx_change_pct == 1.5
        assert ctx.market_sentiment == "bullish"

    def test_spx_bearish(self):
        indices = [make_index("^GSPC", 4500.0, -1.5)]
        ctx = analyze_market_context(indices)
        assert ctx.spx_change_pct == -1.5
        assert ctx.market_sentiment == "bearish"

    def test_ndx_sharp_drop(self):
        indices = [make_index("^IXIC", 14000.0, -2.5)]
        ctx = analyze_market_context(indices)
        assert ctx.ndx_change_pct == -2.5
        assert ctx.market_sentiment == "bearish"
        assert ctx.confidence_adjustment == -0.05
        assert "tech weakness" in ctx.risk_warning

    def test_combined_vix_and_ndx_penalty(self):
        # VIX elevated (-0.08) + NDX < -2% should cap at -0.15
        indices = [
            make_index("^VIX", 28.0, 0.0),
            make_index("^IXIC", 14000.0, -3.0),
        ]
        ctx = analyze_market_context(indices)
        assert ctx.volatility_regime == "elevated"
        assert ctx.confidence_adjustment == -0.13  # -0.08 - 0.05

    def test_combined_spx_ndx_sentiment(self):
        indices = [
            make_index("^GSPC", 4500.0, 0.5),
            make_index("^IXIC", 14000.0, 1.5),
        ]
        ctx = analyze_market_context(indices)
        # avg_change = (0.5 + 1.5) / 2 = 1.0, exactly at threshold
        assert ctx.market_sentiment == "neutral"

    def test_vix_symbol_variants(self):
        # Test VIX symbol variants
        for sym in ("^VIX", "VIX"):
            ctx = analyze_market_context([make_index(sym, 25.0, 0.0)])
            assert ctx.vix_level == 25.0

    def test_spx_symbol_variants(self):
        for sym in ("^GSPC", "SPX"):
            ctx = analyze_market_context([make_index(sym, 4500.0, 1.0)])
            assert ctx.spx_change_pct == 1.0

    def test_ndx_symbol_variants(self):
        for sym in ("^IXIC", "NDX"):
            ctx = analyze_market_context([make_index(sym, 14000.0, -1.0)])
            assert ctx.ndx_change_pct == -1.0


class TestAdjustConfidence:
    def test_no_market_context(self):
        # When market_context is None, base confidence unchanged
        result = adjust_confidence_for_market(0.7, "support", None)  # type: ignore[arg-type]
        assert result == 0.7

    def test_bullish_boosts_support(self):
        ctx = MarketContext(market_sentiment="bullish", confidence_adjustment=0.0)
        result = adjust_confidence_for_market(0.7, "support", ctx)
        assert result == pytest.approx(0.73)

    def test_bullish_reduces_resistance(self):
        ctx = MarketContext(market_sentiment="bullish", confidence_adjustment=0.0)
        result = adjust_confidence_for_market(0.7, "resistance", ctx)
        assert result == pytest.approx(0.67)

    def test_bearish_boosts_resistance(self):
        ctx = MarketContext(market_sentiment="bearish", confidence_adjustment=0.0)
        result = adjust_confidence_for_market(0.7, "resistance", ctx)
        assert result == pytest.approx(0.73)

    def test_bearish_reduces_support(self):
        ctx = MarketContext(market_sentiment="bearish", confidence_adjustment=0.0)
        result = adjust_confidence_for_market(0.7, "support", ctx)
        assert result == pytest.approx(0.67)

    def test_vix_high_penalty(self):
        ctx = MarketContext(volatility_regime="high", confidence_adjustment=-0.15)
        result = adjust_confidence_for_market(0.8, "support", ctx)
        assert result == pytest.approx(0.65)

    def test_clamping_minimum(self):
        ctx = MarketContext(confidence_adjustment=-0.5)
        result = adjust_confidence_for_market(0.2, "support", ctx)
        assert result == 0.1  # clamped to minimum

    def test_clamping_maximum(self):
        ctx = MarketContext(confidence_adjustment=0.5)
        result = adjust_confidence_for_market(0.9, "support", ctx)
        assert result == 0.99  # clamped to maximum


class TestFormatMarketSummary:
    def test_full_context(self):
        ctx = MarketContext(
            vix_level=25.0,
            spx_change_pct=1.2,
            ndx_change_pct=-0.5,
            market_sentiment="bullish",
            volatility_regime="normal",
            position_size_factor=1.0,
        )
        summary = format_market_summary(ctx)
        assert "VIX: 25.00" in summary
        assert "SPX Change: +1.20%" in summary
        assert "NDX Change: -0.50%" in summary
        assert "bullish" in summary

    def test_with_risk_warning(self):
        ctx = MarketContext(
            vix_level=35.0,
            volatility_regime="high",
            risk_warning="Avoid new positions",
        )
        summary = format_market_summary(ctx)
        assert "Avoid new positions" in summary

    def test_partial_context(self):
        ctx = MarketContext(vix_level=20.0)
        summary = format_market_summary(ctx)
        assert "VIX: 20.00" in summary
        assert "SPX Change" not in summary

"""Tests for left/right side LEAPS strategies."""

from datetime import date, timedelta

from src.agents.strategy_exec.strategies.base import discover_strategies
from src.agents.strategy_exec.strategies.left_side_leaps import LeftSideLeapsStrategy
from src.agents.strategy_exec.strategies.right_side_leaps import RightSideLeapsStrategy
from src.models import OptionContract, OptionType, SupportResistanceLevel


def make_option_contract(strike=100.0, delta_val=0.7, expiry_days=365):
    return OptionContract.model_construct(
        symbol="AAPL",
        underlying="AAPL",
        contract_symbol="AAPL250117C00100000",
        strike=strike,
        expiry=date.today() + timedelta(days=expiry_days),
        option_type=OptionType.CALL,
        last_price=5.0,
        delta=delta_val,
        mid_price=5.0,
        is_leaps=True,
    )


class MockOptionsChain:
    spot_price = 100.0
    iv_rank = 30

    def __init__(self):
        self.calls = [make_option_contract()]
        self.puts = []


class MockValuation:
    is_undervalued = True
    discount_to_fair = 15.0
    fair_estimate = 115.0


class MockMarketContext:
    volatility_regime = "normal"
    vix_level = 15.0
    leaps_call_enabled = True
    leaps_confidence_delta = 0.0
    sma_trend = "bullish"
    technical_rsi = 55
    relative_volume = 1.5
    macro_regime = "risk_on"
    technical_grade = "B"


class TestStrategyDiscovery:
    def test_discover_5_strategies(self):
        strategies = discover_strategies()
        names = {s.name for s in strategies}
        assert len(strategies) >= 5, f"Expected >=5, got {len(strategies)}: {names}"
        assert "leaps_call" in names
        assert "bull_spread" in names
        assert "covered_call" in names
        assert "left_side_leaps" in names
        assert "right_side_leaps" in names


class TestLeftSideLeaps:
    def test_all_5_conditions_met(self):
        strategy = LeftSideLeapsStrategy()
        support = SupportResistanceLevel(
            price=97.5, level_type="support",
            confidence=0.8, source="volume_profile",
        )
        result = strategy.generate(
            symbol="AAPL",
            options_chain=MockOptionsChain(),
            support_levels=[support],
            resistance_levels=[],
            valuation_range=MockValuation(),
            current_price=100.0,
            market_context=MockMarketContext(),
        )
        assert result is not None
        assert result.recommendation_type == "left_side_leaps"
        assert result.confidence > 0.5

    def test_insufficient_conditions_returns_none(self):
        strategy = LeftSideLeapsStrategy()
        chain = MockOptionsChain()
        chain.iv_rank = 80  # IV high → not met
        result = strategy.generate(
            symbol="AAPL",
            options_chain=chain,
            support_levels=[],
            resistance_levels=[],
            valuation_range=None,
            current_price=100.0,
            market_context=None,
        )
        assert result is None


class TestRightSideLeaps:
    def test_trend_momentum_vol_regime_met(self):
        strategy = RightSideLeapsStrategy()
        ctx = MockMarketContext()
        ctx.sma_trend = "bullish"
        ctx.technical_rsi = 55
        ctx.relative_volume = 1.5
        ctx.macro_regime = "risk_on"

        result = strategy.generate(
            symbol="AAPL",
            options_chain=MockOptionsChain(),
            support_levels=[],
            resistance_levels=[],
            valuation_range=None,
            current_price=100.0,
            market_context=ctx,
        )
        assert result is not None
        assert result.recommendation_type == "right_side_leaps"

    def test_overbought_rsi_blocks(self):
        strategy = RightSideLeapsStrategy()
        ctx = MockMarketContext()
        ctx.technical_rsi = 75  # overbought, won't satisfy RSI 45-65
        ctx.sma_trend = "bearish"  # also not bullish
        ctx.relative_volume = 0.8  # also not expanding

        result = strategy.generate(
            symbol="AAPL",
            options_chain=MockOptionsChain(),
            support_levels=[],
            resistance_levels=[],
            valuation_range=None,
            current_price=100.0,
            market_context=ctx,
        )
        # sma=bearish, rsi=75(no), vol=0.8(no), regime=risk_on(yes) → 1/4 → None
        assert result is None

    def test_no_market_context_blocks(self):
        strategy = RightSideLeapsStrategy()
        result = strategy.generate(
            symbol="AAPL",
            options_chain=MockOptionsChain(),
            support_levels=[],
            resistance_levels=[],
            valuation_range=None,
            current_price=100.0,
            market_context=None,
        )
        assert result is None
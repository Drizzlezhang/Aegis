"""Tests for cost_model.py — commission and slippage implementations."""


import pytest

from src.backtest.cost_model import (
    ATRAdaptiveSlippage,
    CommissionModel,
    CostModel,
    FixedBpsSlippage,
    FixedCommission,
    PercentCommission,
    SlippageModel,
    TieredCommission,
    VolumeWeightedSlippage,
)


class _FakeTrade:
    """Minimal trade-like object for testing cost models."""

    def __init__(self, shares: float, price: float, volume: float | None = None):
        self.shares = shares
        self.price = price
        self.volume = volume if volume is not None else shares


# ── Commission Tests ──────────────────────────────────────────────


class TestFixedCommission:
    def test_basic_calculation(self):
        """AC-1: FixedCommission 计算 100 股 × $150 佣金 = $1.0"""
        model = FixedCommission(per_share=0.005, min_total=1.0)
        trade = _FakeTrade(shares=100, price=150.0)
        cost = model.calculate(trade)
        # 100 * 0.005 = 0.5, but min_total=1.0 → 1.0
        assert cost == pytest.approx(1.0)

    def test_min_total_kicks_in(self):
        """Small trade should hit min_total floor."""
        model = FixedCommission(per_share=0.005, min_total=1.0)
        trade = _FakeTrade(shares=10, price=50.0)
        cost = model.calculate(trade)
        # 10 * 0.005 = 0.05, min_total=1.0 → 1.0
        assert cost == pytest.approx(1.0)

    def test_large_trade_exceeds_min(self):
        """Large trade should use per_share rate."""
        model = FixedCommission(per_share=0.005, min_total=1.0)
        trade = _FakeTrade(shares=1000, price=100.0)
        cost = model.calculate(trade)
        # 1000 * 0.005 = 5.0 > 1.0 → 5.0
        assert cost == pytest.approx(5.0)

    def test_zero_shares(self):
        model = FixedCommission(per_share=0.005, min_total=1.0)
        trade = _FakeTrade(shares=0, price=100.0)
        cost = model.calculate(trade)
        assert cost == pytest.approx(1.0)  # min_total


class TestPercentCommission:
    def test_rate_calculation(self):
        """AC-2: PercentCommission(rate=0.001, min_total=5.0) 大单正确取 rate"""
        model = PercentCommission(rate=0.001, min_total=5.0)
        trade = _FakeTrade(shares=1000, price=100.0)
        cost = model.calculate(trade)
        # 1000 * 100 * 0.001 = 100.0 > 5.0 → 100.0
        assert cost == pytest.approx(100.0)

    def test_min_total_kicks_in(self):
        """AC-2: 小单取 min_total"""
        model = PercentCommission(rate=0.001, min_total=5.0)
        trade = _FakeTrade(shares=10, price=50.0)
        cost = model.calculate(trade)
        # 10 * 50 * 0.001 = 0.5, min_total=5.0 → 5.0
        assert cost == pytest.approx(5.0)

    def test_zero_notional(self):
        model = PercentCommission(rate=0.001, min_total=5.0)
        trade = _FakeTrade(shares=0, price=100.0)
        cost = model.calculate(trade)
        assert cost == pytest.approx(5.0)


class TestTieredCommission:
    def test_tier_switching(self):
        """AC-3: TieredCommission 按 volume 阶梯切换费率"""
        tiers = [
            (100, 0.01),    # ≤100 shares: $0.01/share
            (500, 0.005),   # ≤500 shares: $0.005/share
            (float("inf"), 0.003),  # >500 shares: $0.003/share
        ]
        model = TieredCommission(tiers=tiers)

        # Tier 1: 50 shares → 50 * 0.01 = 0.5
        assert model.calculate(_FakeTrade(shares=50, price=100)) == pytest.approx(0.5)
        # Tier 2: 200 shares → 200 * 0.005 = 1.0
        assert model.calculate(_FakeTrade(shares=200, price=100)) == pytest.approx(1.0)
        # Tier 3: 1000 shares → 1000 * 0.003 = 3.0
        assert model.calculate(_FakeTrade(shares=1000, price=100)) == pytest.approx(3.0)

    def test_boundary(self):
        """Boundary: exactly at tier threshold."""
        tiers = [(100, 0.01), (float("inf"), 0.005)]
        model = TieredCommission(tiers=tiers)
        # 100 shares → tier 1: 100 * 0.01 = 1.0
        assert model.calculate(_FakeTrade(shares=100, price=100)) == pytest.approx(1.0)
        # 101 shares → tier 2: 101 * 0.005 = 0.505
        assert model.calculate(_FakeTrade(shares=101, price=100)) == pytest.approx(0.505)

    def test_empty_tiers_raises(self):
        with pytest.raises(ValueError, match="tiers"):
            TieredCommission(tiers=[])


# ── Slippage Tests ─────────────────────────────────────────────────


class TestFixedBpsSlippage:
    def test_basic_calculation(self):
        """AC-4: FixedBpsSlippage(bps=2.0) 计算正确"""
        model = FixedBpsSlippage(bps=2.0)
        trade = _FakeTrade(shares=100, price=150.0)
        cost = model.calculate(trade)
        # 100 * 150 * 2.0 / 10000 = 3.0
        assert cost == pytest.approx(3.0)

    def test_zero_bps(self):
        model = FixedBpsSlippage(bps=0.0)
        trade = _FakeTrade(shares=100, price=150.0)
        assert model.calculate(trade) == pytest.approx(0.0)


class TestVolumeWeightedSlippage:
    def test_large_order_more_slippage(self):
        """AC-5: VolumeWeightedSlippage 大单滑点 > 小单"""
        model = VolumeWeightedSlippage(impact_coef=0.1)
        small = _FakeTrade(shares=100, price=100.0)
        large = _FakeTrade(shares=10000, price=100.0)
        assert model.calculate(large) > model.calculate(small)

    def test_zero_shares(self):
        model = VolumeWeightedSlippage(impact_coef=0.1)
        trade = _FakeTrade(shares=0, price=100.0)
        assert model.calculate(trade) == pytest.approx(0.0)


class TestATRAdaptiveSlippage:
    def test_high_volatility_more_slippage(self):
        """AC-6: ATRAdaptiveSlippage 高波动时段滑点 > 低波动"""
        model = ATRAdaptiveSlippage(atr_multiple=0.5)
        # High ATR trade
        high_vol = _FakeTrade(shares=100, price=100.0, volume=100)
        high_vol.atr = 5.0  # type: ignore[attr-defined]
        # Low ATR trade
        low_vol = _FakeTrade(shares=100, price=100.0, volume=100)
        low_vol.atr = 1.0  # type: ignore[attr-defined]
        assert model.calculate(high_vol) > model.calculate(low_vol)

    def test_no_atr_fallback(self):
        """When trade has no ATR, fall back to price-based estimate."""
        model = ATRAdaptiveSlippage(atr_multiple=0.5)
        trade = _FakeTrade(shares=100, price=100.0)
        cost = model.calculate(trade)
        # Should not crash; uses 1% of price as fallback ATR
        assert cost > 0


# ── Abstract Base Class Tests ──────────────────────────────────────


class TestCostModelABC:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            CostModel()  # type: ignore[abstract]

    def test_commission_is_cost_model(self):
        assert issubclass(CommissionModel, CostModel)

    def test_slippage_is_cost_model(self):
        assert issubclass(SlippageModel, CostModel)


# ── E2E PnL Test ───────────────────────────────────────────────────


class TestE2EPnL:
    def test_pnl_vs_excel(self):
        """AC-7: 已知 trade 序列 PnL 与 Excel 对比误差 < 0.01"""
        commission = FixedCommission(per_share=0.005, min_total=1.0)
        slippage = FixedBpsSlippage(bps=1.0)

        # Simulate a round-trip: buy 100 shares @ $150, sell @ $155
        buy_trade = _FakeTrade(shares=100, price=150.0)
        sell_trade = _FakeTrade(shares=100, price=155.0)

        buy_cost = commission.calculate(buy_trade) + slippage.calculate(buy_trade)
        sell_cost = commission.calculate(sell_trade) + slippage.calculate(sell_trade)

        # Gross PnL: (155 - 150) * 100 = 500
        gross_pnl = (155.0 - 150.0) * 100
        # Costs: buy 1.0 + 1.5 = 2.5, sell 1.0 + 1.55 = 2.55, total = 5.05
        total_cost = buy_cost + sell_cost
        net_pnl = gross_pnl - total_cost

        # Excel: 500 - 5.05 = 494.95
        expected = 494.95
        assert net_pnl == pytest.approx(expected, abs=0.01)

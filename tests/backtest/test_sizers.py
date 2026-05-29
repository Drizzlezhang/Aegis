"""Tests for sizers.py — Position sizing strategies."""

from __future__ import annotations

import pytest

from src.backtest.sizers import (
    FixedFractionalSizer,
    KellySizer,
    PositionSizer,
    RiskParitySizer,
)


class TestFixedFractionalSizer:
    def test_basic_calculation(self):
        """AC-14: FixedFractionalSizer 仓位 = equity × fraction."""
        sizer = FixedFractionalSizer(fraction=0.1)
        size = sizer.size(equity=100000, signal_confidence=0.8)
        assert size == pytest.approx(10000)

    def test_zero_equity(self):
        sizer = FixedFractionalSizer(fraction=0.1)
        size = sizer.size(equity=0, signal_confidence=0.8)
        assert size == 0.0

    def test_different_fractions(self):
        sizer_05 = FixedFractionalSizer(fraction=0.05)
        sizer_20 = FixedFractionalSizer(fraction=0.20)
        assert sizer_20.size(100000, 0.8) > sizer_05.size(100000, 0.8)


class TestKellySizer:
    def test_basic_calculation(self):
        """Kelly formula: f = win_rate - (1 - win_rate) / win_loss_ratio."""
        sizer = KellySizer(win_rate=0.55, win_loss_ratio=1.5, cap=0.25)
        size = sizer.size(equity=100000, signal_confidence=0.8)
        # Kelly fraction: 0.55 - 0.45/1.5 = 0.55 - 0.30 = 0.25
        expected = 100000 * 0.25
        assert size == pytest.approx(expected)

    def test_capped(self):
        """AC-15: KellySizer 仓位 ≤ cap."""
        sizer = KellySizer(win_rate=0.80, win_loss_ratio=3.0, cap=0.25)
        size = sizer.size(equity=100000, signal_confidence=0.8)
        # Kelly fraction: 0.80 - 0.20/3.0 = 0.733, capped at 0.25
        assert size <= 100000 * 0.25

    def test_negative_kelly_returns_zero(self):
        """Negative Kelly fraction → zero position."""
        sizer = KellySizer(win_rate=0.30, win_loss_ratio=1.0, cap=0.25)
        size = sizer.size(equity=100000, signal_confidence=0.8)
        assert size == 0.0

    def test_zero_equity(self):
        sizer = KellySizer(win_rate=0.55, win_loss_ratio=1.5, cap=0.25)
        size = sizer.size(equity=0, signal_confidence=0.8)
        assert size == 0.0


class TestRiskParitySizer:
    def test_high_vol_low_position(self):
        """AC-16: RiskParitySizer 高波动 → 低仓位."""
        sizer = RiskParitySizer(target_vol=0.15, lookback=20)
        size_high_vol = sizer.size(equity=100000, signal_confidence=0.8, volatility=0.40)
        size_low_vol = sizer.size(equity=100000, signal_confidence=0.8, volatility=0.10)
        assert size_high_vol < size_low_vol

    def test_default_volatility(self):
        """When volatility not provided, uses default."""
        sizer = RiskParitySizer(target_vol=0.15, lookback=20)
        size = sizer.size(equity=100000, signal_confidence=0.8)
        # Default vol = 0.20 → size = 100000 * 0.15 / 0.20 = 75000
        assert size == pytest.approx(75000)

    def test_zero_vol_returns_zero(self):
        sizer = RiskParitySizer(target_vol=0.15, lookback=20)
        size = sizer.size(equity=100000, signal_confidence=0.8, volatility=0.0)
        assert size == 0.0

    def test_zero_equity(self):
        sizer = RiskParitySizer(target_vol=0.15, lookback=20)
        size = sizer.size(equity=0, signal_confidence=0.8)
        assert size == 0.0


class TestSizerDifferentiation:
    """AC-17: 同信号序列不同 sizer 资金曲线差异 > 5%."""

    def test_different_sizers_produce_different_sizes(self):
        equity = 100000
        confidence = 0.8

        fixed = FixedFractionalSizer(fraction=0.1).size(equity, confidence)
        kelly = KellySizer(win_rate=0.55, win_loss_ratio=1.5, cap=0.25).size(equity, confidence)
        rp = RiskParitySizer(target_vol=0.15, lookback=20).size(equity, confidence)

        sizes = [fixed, kelly, rp]
        # At least two sizers should differ by > 5% of equity
        max_diff = max(sizes) - min(sizes)
        assert max_diff > equity * 0.05, (
            f"Sizers too similar: fixed={fixed:.0f}, kelly={kelly:.0f}, rp={rp:.0f}"
        )


class TestPositionSizerABC:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            PositionSizer()  # type: ignore[abstract]

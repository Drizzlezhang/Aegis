"""Tests for exit_rules.py — Stop-Loss / Take-Profit / Trailing Stop."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.backtest.exit_rules import (
    ATRMultipleStop,
    ExitRule,
    FixedPctStop,
    TrailingStop,
)


@dataclass
class _FakeBar:
    """Minimal bar for testing exit rules."""

    close: float
    high: float
    low: float
    open: float = 0.0
    atr: float = 1.0


class TestFixedPctStop:
    def test_stop_loss_triggered(self):
        """AC-18: FixedPctStop 触发后返回 True."""
        rule = FixedPctStop(stop_pct=0.05, target_pct=0.10)
        # Entry at 100, current price 94 → -6% → stop triggered
        assert rule.should_exit(entry_price=100.0, current_bar=_FakeBar(close=94.0, high=95.0, low=93.0))

    def test_take_profit_triggered(self):
        """Take-profit triggers at target."""
        rule = FixedPctStop(stop_pct=0.05, target_pct=0.10)
        # Entry at 100, current price 111 → +11% → target triggered
        assert rule.should_exit(entry_price=100.0, current_bar=_FakeBar(close=111.0, high=112.0, low=110.0))

    def test_no_trigger_in_range(self):
        """Price within range → no exit."""
        rule = FixedPctStop(stop_pct=0.05, target_pct=0.10)
        assert not rule.should_exit(entry_price=100.0, current_bar=_FakeBar(close=102.0, high=103.0, low=101.0))

    def test_exit_price_is_next_bar_open(self):
        """AC-18: 触发后下根 bar 开盘价平仓."""
        rule = FixedPctStop(stop_pct=0.05, target_pct=0.10)
        exit_price = rule.get_exit_price(current_bar=_FakeBar(close=94.0, high=95.0, low=93.0, open=95.0))
        assert exit_price == 95.0  # Next bar open (conservative)

    def test_stop_loss_on_crash(self):
        """AC-21: 已知大跌 bar 序列下 stop-loss 触发且损失符合预期."""
        rule = FixedPctStop(stop_pct=0.05, target_pct=0.10)
        # Entry at 100, crash to 90 → -10% → stop triggered
        assert rule.should_exit(entry_price=100.0, current_bar=_FakeBar(close=90.0, high=95.0, low=88.0))
        exit_price = rule.get_exit_price(current_bar=_FakeBar(close=90.0, high=95.0, low=88.0, open=91.0))
        loss_pct = (exit_price - 100.0) / 100.0
        # Loss should be close to stop_pct (with gap allowance)
        assert loss_pct <= -0.05  # At least 5% loss


class TestATRMultipleStop:
    def test_dynamic_threshold(self):
        """AC-19: ATRMultipleStop 动态阈值随波动变化."""
        rule = ATRMultipleStop(atr_lookback=14, atr_mult=2.0)
        # Low ATR bar → tight stop
        low_atr_bar = _FakeBar(close=100.0, high=101.0, low=99.0, atr=1.0)
        # High ATR bar → wide stop
        high_atr_bar = _FakeBar(close=100.0, high=101.0, low=99.0, atr=5.0)

        # Entry at 100, ATR=1 → stop at 100 - 2*1 = 98
        assert rule.should_exit(entry_price=100.0, current_bar=_FakeBar(close=97.0, high=98.0, low=96.0, atr=1.0))
        # Entry at 100, ATR=5 → stop at 100 - 2*5 = 90
        assert not rule.should_exit(entry_price=100.0, current_bar=_FakeBar(close=97.0, high=98.0, low=96.0, atr=5.0))

    def test_no_atr_fallback(self):
        """When bar has no ATR, use 1% of price."""
        rule = ATRMultipleStop(atr_lookback=14, atr_mult=2.0)
        bar = _FakeBar(close=97.0, high=98.0, low=96.0)
        bar.atr = 0  # type: ignore[attr-defined]
        # Fallback ATR = 100 * 0.01 = 1.0, stop = 100 - 2*1 = 98
        assert rule.should_exit(entry_price=100.0, current_bar=bar)


class TestTrailingStop:
    def test_ratchet_up(self):
        """AC-20: TrailingStop 跟随最高价上移."""
        rule = TrailingStop(activation_pct=0.05, trail_pct=0.03)
        # Entry at 100, activation at 105
        # Price goes to 106 → highest = 106, trail stop = 106 * (1 - 0.03) = 102.82
        bar1 = _FakeBar(close=106.0, high=107.0, low=105.0)
        assert not rule.should_exit(entry_price=100.0, current_bar=bar1)
        assert rule._highest_price == pytest.approx(106.0)  # type: ignore[attr-defined]

        # Price drops to 102 → below trail stop → exit
        bar2 = _FakeBar(close=102.0, high=103.0, low=101.0)
        assert rule.should_exit(entry_price=100.0, current_bar=bar2)

    def test_not_activated_yet(self):
        """No exit before activation price reached."""
        rule = TrailingStop(activation_pct=0.05, trail_pct=0.03)
        # Price at 103 → not yet activated (need 105)
        assert not rule.should_exit(entry_price=100.0, current_bar=_FakeBar(close=103.0, high=104.0, low=102.0))

    def test_reset_on_new_entry(self):
        """Highest price resets when checking a new position."""
        rule = TrailingStop(activation_pct=0.05, trail_pct=0.03)
        # First position
        rule.should_exit(entry_price=100.0, current_bar=_FakeBar(close=110.0, high=111.0, low=109.0))
        assert rule._highest_price == pytest.approx(110.0)  # type: ignore[attr-defined]
        # New position at different entry → reset
        rule.should_exit(entry_price=200.0, current_bar=_FakeBar(close=205.0, high=206.0, low=204.0))
        assert rule._highest_price == pytest.approx(205.0)  # type: ignore[attr-defined]


class TestExitRuleABC:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            ExitRule()  # type: ignore[abstract]

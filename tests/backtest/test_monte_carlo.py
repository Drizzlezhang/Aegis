"""Tests for monte_carlo.py — Monte Carlo simulation."""

from __future__ import annotations

import pytest

from src.backtest.monte_carlo import MonteCarloSimulator


class _FakeTrade:
    def __init__(self, pnl: float):
        self.pnl = pnl


def _make_trades(pnls: list[float]) -> list[_FakeTrade]:
    return [_FakeTrade(p) for p in pnls]


class TestMonteCarlo:
    def test_var_cvar_output(self):
        """AC-24: MC bootstrap N=1000 产出 VaR(95%) / CVaR(95%)."""
        # Trades with mixed outcomes — some paths can lose
        trades = _make_trades([200.0] * 30 + [-300.0] * 30 + [50.0] * 40)
        sim = MonteCarloSimulator(seed=42)
        result = sim.run(trades, n_iterations=1000)

        assert result.n_iterations == 1000
        assert result.seed == 42
        # VaR should be negative (loss) with this mixed distribution
        assert result.var_95 < 0, f"Expected negative VaR, got {result.var_95}"
        assert result.cvar_95 <= result.var_95  # CVaR ≤ VaR (more extreme)
        assert len(result.return_distribution) == 1000

    def test_var_ordering(self):
        """AC-25: 高 Sharpe 策略 VaR 优于低 Sharpe."""
        # High Sharpe: mostly wins, small losses
        high_sharpe = _make_trades([100.0] * 80 + [-20.0] * 20)
        # Low Sharpe: mixed wins and losses
        low_sharpe = _make_trades([50.0] * 50 + [-50.0] * 50)

        sim = MonteCarloSimulator(seed=42)
        result_high = sim.run(high_sharpe, n_iterations=500)
        result_low = sim.run(low_sharpe, n_iterations=500)

        # High Sharpe should have better (less negative) VaR
        assert result_high.var_95 > result_low.var_95, (
            f"High Sharpe VaR={result_high.var_95:.2f} should be > Low Sharpe VaR={result_low.var_95:.2f}"
        )

    def test_ruin_probability(self):
        """AC-26: 破产概率计算正确."""
        # Trades that always lose → high ruin probability
        losing_trades = _make_trades([-100.0] * 100)
        sim = MonteCarloSimulator(seed=42)
        result = sim.run(losing_trades, n_iterations=500, initial_capital=1000.0)

        # With 100 losing trades of -100 each, ruin is certain
        assert result.ruin_probability > 0.9

    def test_reproducibility(self):
        """Same seed → same result."""
        trades = _make_trades([100.0] * 60 + [-50.0] * 40)
        sim1 = MonteCarloSimulator(seed=42)
        sim2 = MonteCarloSimulator(seed=42)
        r1 = sim1.run(trades, n_iterations=100)
        r2 = sim2.run(trades, n_iterations=100)
        assert r1.mean_return == pytest.approx(r2.mean_return)
        assert r1.var_95 == pytest.approx(r2.var_95)

    def test_empty_trades(self):
        """Empty trades → zero results."""
        sim = MonteCarloSimulator(seed=42)
        result = sim.run([], n_iterations=100)
        assert result.n_iterations == 100
        assert result.mean_return == 0.0
        assert result.ruin_probability == 0.0

    def test_single_trade(self):
        """Single trade → bootstrap still works."""
        trades = _make_trades([100.0])
        sim = MonteCarloSimulator(seed=42)
        result = sim.run(trades, n_iterations=100)
        assert result.n_iterations == 100
        assert len(result.return_distribution) == 100

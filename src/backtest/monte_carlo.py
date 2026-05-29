"""Monte Carlo simulation for backtest v3.

Uses bootstrap resampling of historical trades to estimate
the distribution of possible outcomes, VaR, CVaR, and ruin probability.

Exports:
    MonteCarloSimulator — bootstrap-based MC simulation
"""

from __future__ import annotations

import random
from typing import Any

from src.models.backtest import MCSimulationResult


class MonteCarloSimulator:
    """Bootstrap-based Monte Carlo simulation for trade PnL sequences.

    Resamples historical trades with replacement to generate N alternative
    equity paths, then computes VaR(95%), CVaR(95%), and ruin probability.

    Args:
        seed: Random seed for reproducibility.
    """

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed

    def run(
        self,
        trades: list[Any],
        n_iterations: int = 1000,
        initial_capital: float = 100000.0,
    ) -> MCSimulationResult:
        """Run Monte Carlo simulation.

        Args:
            trades: List of trade objects with .pnl attribute.
            n_iterations: Number of bootstrap iterations.
            initial_capital: Starting capital for each simulation path.

        Returns:
            MCSimulationResult with VaR, CVaR, ruin probability, etc.
        """
        rng = random.Random(self.seed)

        if not trades:
            return MCSimulationResult(
                n_iterations=n_iterations,
                seed=self.seed,
            )

        pnls = [t.pnl for t in trades if t.pnl is not None]
        if not pnls:
            return MCSimulationResult(
                n_iterations=n_iterations,
                seed=self.seed,
            )

        n_trades = len(pnls)
        final_equities: list[float] = []

        for _ in range(n_iterations):
            # Bootstrap resample
            sampled = [pnls[rng.randint(0, n_trades - 1)] for _ in range(n_trades)]
            final_equity = initial_capital + sum(sampled)
            final_equities.append(final_equity)

        # Sort for quantile calculations
        sorted_equities = sorted(final_equities)

        # VaR(95%): 5th percentile of final equity
        var_idx = int(n_iterations * 0.05)
        var_95_equity = sorted_equities[var_idx]
        var_95 = (var_95_equity - initial_capital) / initial_capital

        # CVaR(95%): mean of worst 5%
        worst = sorted_equities[: max(var_idx, 1)]
        cvar_95_equity = sum(worst) / len(worst)
        cvar_95 = (cvar_95_equity - initial_capital) / initial_capital

        # Ruin probability: fraction where final equity <= 0
        ruin_count = sum(1 for e in final_equities if e <= 0)
        ruin_probability = ruin_count / n_iterations

        # Return distribution (as returns relative to initial capital)
        return_distribution = [(e - initial_capital) / initial_capital for e in final_equities]

        mean_return = sum(return_distribution) / n_iterations
        median_return = sorted(return_distribution)[n_iterations // 2]
        std_return = (
            sum((r - mean_return) ** 2 for r in return_distribution) / n_iterations
        ) ** 0.5

        return MCSimulationResult(
            n_iterations=n_iterations,
            seed=self.seed,
            mean_return=mean_return,
            median_return=median_return,
            std_return=std_return,
            var_95=var_95,
            cvar_95=cvar_95,
            ruin_probability=ruin_probability,
            return_distribution=return_distribution,
        )

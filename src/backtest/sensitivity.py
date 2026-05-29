"""Parameter sensitivity analysis for backtest v3.

Sweeps over a parameter range, runs backtests for each value,
and identifies "parameter cliffs" where small changes cause large
performance drops.

Exports:
    SensitivityAnalyzer — grid search + cliff detection
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.models.backtest import SweepResult


class SensitivityAnalyzer:
    """Parameter sensitivity analyzer.

    Performs grid search over a single parameter, runs a backtest
    function for each value, and detects parameter cliffs.

    Usage:
        analyzer = SensitivityAnalyzer()
        result = analyzer.sweep(
            param_name="ma_window",
            param_range=(10, 50, 5),
            run_fn=lambda v: run_backtest_with_param(v),
        )
    """

    def sweep(
        self,
        param_name: str,
        param_range: tuple[float, float, float],
        run_fn: Callable[[float], Any],
    ) -> SweepResult:
        """Sweep a parameter and collect metrics.

        Args:
            param_name: Name of the parameter being swept.
            param_range: (start, end, step) tuple.
            run_fn: Function that takes a parameter value and returns
                    a result object with .metrics (sharpe_ratio,
                    total_return, max_drawdown).

        Returns:
            SweepResult with data points and detected cliffs.

        Raises:
            ValueError: If step <= 0 or start > end.
        """
        start, end, step = param_range
        if step <= 0:
            raise ValueError(f"step must be positive, got {step}")
        if start > end:
            raise ValueError(f"start ({start}) must be <= end ({end})")

        data_points: list[dict[str, Any]] = []
        value = start
        while value <= end + 1e-9:  # float tolerance
            result = run_fn(value)
            metrics = result.metrics
            data_points.append({
                "param_value": value,
                "sharpe_ratio": metrics.sharpe_ratio,
                "total_return": metrics.total_return,
                "max_drawdown": metrics.max_drawdown,
            })
            value += step

        # Detect cliffs: 5% param change → metric drops >20%
        cliffs = self._detect_cliffs(data_points, param_range)

        return SweepResult(
            param_name=param_name,
            data_points=data_points,
            cliffs=cliffs,
        )

    def _detect_cliffs(
        self,
        data_points: list[dict[str, Any]],
        param_range: tuple[float, float, float],
    ) -> list[dict[str, Any]]:
        """Detect parameter cliffs where small change → large metric drop."""
        cliffs: list[dict[str, Any]] = []
        if len(data_points) < 2:
            return cliffs

        start, end, step = param_range
        param_span = end - start
        if param_span <= 0:
            return cliffs

        metrics_to_check = ["sharpe_ratio", "total_return", "max_drawdown"]

        for i in range(1, len(data_points)):
            prev = data_points[i - 1]
            curr = data_points[i]
            param_change_pct = abs(curr["param_value"] - prev["param_value"]) / param_span

            # Only flag if param change is small (≤ 10% of range)
            if param_change_pct > 0.10:
                continue

            for metric in metrics_to_check:
                prev_val = prev[metric]
                curr_val = curr[metric]
                if prev_val == 0:
                    continue
                change_pct = (curr_val - prev_val) / abs(prev_val)

                # For max_drawdown, a drop means more negative (worse)
                if metric == "max_drawdown":
                    if prev_val < 0 and curr_val < prev_val * 1.2:  # 20% worse
                        cliffs.append({
                            "param_value": curr["param_value"],
                            "metric": metric,
                            "drop_pct": abs(change_pct) * 100,
                        })
                else:
                    if change_pct < -0.20:  # >20% drop
                        cliffs.append({
                            "param_value": curr["param_value"],
                            "metric": metric,
                            "drop_pct": abs(change_pct) * 100,
                        })

        return cliffs

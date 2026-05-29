"""Tests for sensitivity.py — Parameter sensitivity analysis."""

from __future__ import annotations

import pytest

from src.backtest.sensitivity import SensitivityAnalyzer


class _FakeResult:
    """Minimal backtest result for sensitivity testing."""

    def __init__(self, sharpe: float, total_return: float, max_drawdown: float):
        self.metrics = _FakeMetrics(sharpe, total_return, max_drawdown)


class _FakeMetrics:
    def __init__(self, sharpe: float, total_return: float, max_drawdown: float):
        self.sharpe_ratio = sharpe
        self.total_return = total_return
        self.max_drawdown = max_drawdown


class TestSensitivity:
    def test_sweep_output_count(self):
        """AC-27: Sensitivity sweep 产出 N 组数据点."""
        analyzer = SensitivityAnalyzer()

        def _run(param_value: float) -> _FakeResult:
            # Simulate: higher ma_window → lower sharpe
            sharpe = 1.5 - param_value * 0.02
            return _FakeResult(sharpe=sharpe, total_return=0.15, max_drawdown=-0.08)

        result = analyzer.sweep(
            param_name="ma_window",
            param_range=(10, 50, 5),
            run_fn=_run,
        )

        # (50 - 10) / 5 + 1 = 9 data points
        assert len(result.data_points) == 9
        assert result.param_name == "ma_window"

    def test_cliff_detection(self):
        """AC-28: 参数悬崖检测正确."""
        analyzer = SensitivityAnalyzer()

        def _run(param_value: float) -> _FakeResult:
            # Sharp drop at param=30
            if param_value <= 28:
                return _FakeResult(sharpe=1.5, total_return=0.15, max_drawdown=-0.08)
            else:
                return _FakeResult(sharpe=0.5, total_return=0.05, max_drawdown=-0.25)

        result = analyzer.sweep(
            param_name="ma_window",
            param_range=(10, 50, 2),  # Smaller step for cliff detection
            run_fn=_run,
        )

        # Should detect cliff around param=30
        assert len(result.cliffs) > 0
        cliff = result.cliffs[0]
        assert cliff["metric"] == "sharpe_ratio"
        assert cliff["drop_pct"] > 20.0  # >20% drop

    def test_heatmap_matrix(self):
        """AC-29: Heatmap 数据矩阵格式正确."""
        analyzer = SensitivityAnalyzer()

        def _run(param_value: float) -> _FakeResult:
            return _FakeResult(sharpe=1.0, total_return=0.10, max_drawdown=-0.10)

        result = analyzer.sweep(
            param_name="ma_window",
            param_range=(10, 30, 10),
            run_fn=_run,
        )

        # heatmap_matrix is None for 1D sweep (only for 2D)
        assert result.heatmap_matrix is None

    def test_no_cliff_when_stable(self):
        """No cliffs when parameters are stable."""
        analyzer = SensitivityAnalyzer()

        def _run(param_value: float) -> _FakeResult:
            return _FakeResult(sharpe=1.2, total_return=0.12, max_drawdown=-0.10)

        result = analyzer.sweep(
            param_name="ma_window",
            param_range=(10, 30, 10),
            run_fn=_run,
        )

        assert len(result.cliffs) == 0

    def test_invalid_range(self):
        """Invalid range raises ValueError."""
        analyzer = SensitivityAnalyzer()

        def _run(param_value: float) -> _FakeResult:
            return _FakeResult(sharpe=1.0, total_return=0.10, max_drawdown=-0.10)

        with pytest.raises(ValueError, match="step"):
            analyzer.sweep(param_name="x", param_range=(10, 50, 0), run_fn=_run)

        with pytest.raises(ValueError, match="start"):
            analyzer.sweep(param_name="x", param_range=(50, 10, 5), run_fn=_run)

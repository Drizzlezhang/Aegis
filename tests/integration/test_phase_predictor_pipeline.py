"""Integration tests for PhasePredictor in QuantBrainAgent pipeline."""

from datetime import date, datetime, timedelta

import pytest

from src.agents.quant_brain.phase_predictor import PhasePredictor
from src.models.market import OHLCV
from src.models.scoring import MacroRegime
from src.models.state import AgentState


def _make_ohlcv(n_bars: int = 60) -> list[OHLCV]:
    """Build synthetic OHLCV bars for pipeline integration tests."""
    bars = []
    base_time = datetime(2024, 1, 1)
    for i in range(n_bars):
        close = 100 + i * 0.2
        bars.append(OHLCV(
            symbol="AAPL",
            timestamp=base_time + timedelta(days=i),
            open=close - 0.1,
            high=close + 0.5,
            low=close - 0.5,
            close=close,
            volume=1_000_000,
        ))
    return bars


def _make_state(n_bars: int = 60) -> AgentState:
    """Build AgentState with OHLCV data."""
    return AgentState(
        symbol="AAPL",
        trade_date=date(2024, 3, 1),
        ohlcv_data=_make_ohlcv(n_bars),
    )


class TestPhaseInPipeline:
    """PhasePredictor integration within the agent pipeline."""

    async def test_phase_predictor_standalone_integration(self):
        """state → predict → result stored on state."""
        state = _make_state(60)
        predictor = PhasePredictor()

        result = await predictor.predict(
            ohlcv_data=state.ohlcv_data,
            macro_regime=None,
            valuation_range=state.valuation_range,
            current_price=state.ohlcv_data[-1].close,
        )

        state.trend_phase_result = result

        assert state.trend_phase_result is not None
        assert state.trend_phase_result.phase.value in [
            "accumulation", "markup", "distribution",
            "markdown", "re_accumulation", "re_distribution",
        ]
        assert len(state.trend_phase_result.dimension_scores) == 7

    async def test_phase_predictor_report_append(self):
        """Phase result is correctly appended to analysis_report."""
        state = _make_state(60)
        state.analysis_report = "## Existing Report\nSome content\n"

        predictor = PhasePredictor()
        result = await predictor.predict(
            ohlcv_data=state.ohlcv_data,
            macro_regime=None,
            valuation_range=None,
            current_price=state.ohlcv_data[-1].close,
        )

        state.trend_phase_result = result

        dim_summary = ", ".join(
            f"{d.name}={d.normalized_score:.0f}" for d in result.dimension_scores
        )
        override_note = " [LOW-VOL OVERRIDE]" if result.low_volatility_override else ""
        state.analysis_report += (
            f"\n## Trend Phase (Wyckoff)\n"
            f"Phase: {result.phase.value} (confidence: {result.confidence:.2f}){override_note}\n"
            f"Composite Score: {result.composite_score:.1f}/100\n"
            f"Dimensions: {dim_summary}\n"
        )

        assert "## Trend Phase (Wyckoff)" in state.analysis_report
        assert "Composite Score:" in state.analysis_report
        assert "velocity=" in state.analysis_report
        assert "acceleration=" in state.analysis_report

    async def test_phase_predictor_with_macro_regime(self):
        """MacroRegime risk_on → macro dimension > 50."""
        state = _make_state(60)

        regime = MacroRegime(
            regime="risk_on",
            confidence=0.8,
            vix_signal="low_vol",
            market_trend="bullish",
        )

        predictor = PhasePredictor()
        result = await predictor.predict(
            ohlcv_data=state.ohlcv_data,
            macro_regime=regime,
            valuation_range=None,
            current_price=state.ohlcv_data[-1].close,
        )

        macro_dim = next(d for d in result.dimension_scores if d.name == "macro")
        assert macro_dim.normalized_score > 50

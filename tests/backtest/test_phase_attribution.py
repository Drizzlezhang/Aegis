"""Tests for phase attribution analysis."""

import pytest

from src.backtest.phase_attribution import PhaseAttribution
from src.models.backtest import PipelineBacktestTrade


def _make_trade(
    entry_phase: str,
    pnl: float,
    pnl_percent: float,
    exit_phase: str = "markup",
) -> PipelineBacktestTrade:
    return PipelineBacktestTrade(
        entry_date="2024-01-15",
        exit_date="2024-02-15",
        entry_price=100.0,
        exit_price=100.0 + pnl_percent,
        shares=100,
        pnl=pnl,
        pnl_percent=pnl_percent,
        status="closed",
        entry_phase=entry_phase,
        exit_phase=exit_phase,
        entry_confidence=70.0,
        exit_confidence=65.0,
    )


class TestPhaseAttribution:
    """Tests for PhaseAttribution.analyze()."""

    def test_empty_trades(self):
        """Empty trades returns empty list."""
        result = PhaseAttribution.analyze([], [])
        assert result == []

    def test_single_phase(self):
        """Single phase returns one row."""
        trades = [
            _make_trade("markup", 500.0, 5.0),
            _make_trade("markup", 300.0, 3.0),
        ]
        result = PhaseAttribution.analyze(trades, [])

        assert len(result) == 1
        assert result[0].phase == "markup"
        assert result[0].trades_count == 2
        assert result[0].avg_return == pytest.approx(4.0)
        assert result[0].win_rate == 100.0
        assert result[0].contribution_to_total == 100.0

    def test_multiple_phases(self):
        """Multiple phases return one row per phase."""
        trades = [
            _make_trade("markup", 500.0, 5.0),
            _make_trade("markdown", -200.0, -2.0),
            _make_trade("markup", 300.0, 3.0),
        ]
        result = PhaseAttribution.analyze(trades, [])

        assert len(result) == 2
        phases = {r.phase for r in result}
        assert phases == {"markup", "markdown"}

        markup_row = next(r for r in result if r.phase == "markup")
        assert markup_row.trades_count == 2
        assert markup_row.avg_return == pytest.approx(4.0)

        markdown_row = next(r for r in result if r.phase == "markdown")
        assert markdown_row.trades_count == 1
        assert markdown_row.avg_return == pytest.approx(-2.0)

    def test_contribution_sums_to_100(self):
        """Phase contributions sum to approximately 100%."""
        trades = [
            _make_trade("markup", 600.0, 6.0),
            _make_trade("markdown", -400.0, -4.0),
        ]
        result = PhaseAttribution.analyze(trades, [])

        total_contribution = sum(r.contribution_to_total for r in result)
        assert total_contribution == pytest.approx(100.0)

    def test_win_rate_calculation(self):
        """Win rate is correctly calculated per phase."""
        trades = [
            _make_trade("markup", 500.0, 5.0),
            _make_trade("markup", -100.0, -1.0),
            _make_trade("markup", 200.0, 2.0),
        ]
        result = PhaseAttribution.analyze(trades, [])

        assert len(result) == 1
        assert result[0].win_rate == pytest.approx(66.7, rel=0.01)

    def test_unknown_phase(self):
        """Trades without entry_phase are grouped as 'unknown'."""
        trade = PipelineBacktestTrade(
            entry_date="2024-01-15",
            exit_date="2024-02-15",
            entry_price=100.0,
            exit_price=105.0,
            shares=100,
            pnl=500.0,
            pnl_percent=5.0,
            status="closed",
        )
        result = PhaseAttribution.analyze([trade], [])

        assert len(result) == 1
        assert result[0].phase == "unknown"

    def test_transition_alpha_with_sequence(self):
        """Transition alpha is calculated from phase sequence."""
        trades = [
            _make_trade("markup", 500.0, 5.0),
        ]
        daily_decisions = [
            {"date": "2024-01-01", "price": 100.0, "phase": "markup"},
            {"date": "2024-01-02", "price": 102.0, "phase": "markdown"},
            {"date": "2024-01-03", "price": 101.0, "phase": "markup"},
            {"date": "2024-01-04", "price": 103.0, "phase": "markdown"},
        ]
        result = PhaseAttribution.analyze(trades, daily_decisions)

        assert len(result) == 1
        assert result[0].transition_alpha is not None

    def test_transition_alpha_none_when_no_transition(self):
        """Transition alpha is None when no phase transitions occur."""
        trades = [
            _make_trade("markup", 500.0, 5.0),
        ]
        daily_decisions = [
            {"date": "2024-01-01", "price": 100.0, "phase": "markup"},
            {"date": "2024-01-02", "price": 102.0, "phase": "markup"},
        ]
        result = PhaseAttribution.analyze(trades, daily_decisions)

        assert len(result) == 1
        assert result[0].transition_alpha is None

"""Tests for position sizing based on Wyckoff phase."""

import pytest

from src.agents.debate.phase_evidence import PhaseEvidence
from src.agents.strategy_exec.market_context import adjust_position_for_phase
from src.models.trend_phase import WyckoffPhase


class TestPositionPhaseAdjustment:
    """Tests for phase-aware position sizing."""

    def test_long_bias_increases_position(self):
        """position_bias='long' + high confidence → size * ~1.2."""
        pe = PhaseEvidence(
            phase=WyckoffPhase.MARKUP,
            composite_score=75.0,
            confidence=90.0,
            position_bias="long",
        )
        result = adjust_position_for_phase(1000.0, pe)
        # multiplier = 1.2, confidence_mod = 0.9
        # adjusted = 1.0 + (1.2 - 1.0) * 0.9 = 1.18
        # result = 1000 * 1.18 = 1180
        assert result > 1000.0
        assert result == pytest.approx(1180.0)

    def test_reduce_bias_halves_position(self):
        """position_bias='reduce' → size * ~0.5."""
        pe = PhaseEvidence(
            phase=WyckoffPhase.DISTRIBUTION,
            composite_score=35.0,
            confidence=80.0,
            position_bias="reduce",
        )
        result = adjust_position_for_phase(1000.0, pe)
        # multiplier = 0.5, confidence_mod = 0.8
        # adjusted = 1.0 + (0.5 - 1.0) * 0.8 = 0.6
        # result = 1000 * 0.6 = 600
        assert result < 1000.0
        assert result == pytest.approx(600.0)

    def test_neutral_conservative(self):
        """position_bias='neutral' → size * ~0.8."""
        pe = PhaseEvidence(
            phase=WyckoffPhase.ACCUMULATION,
            composite_score=50.0,
            confidence=30.0,
            position_bias="neutral",
        )
        result = adjust_position_for_phase(1000.0, pe)
        # multiplier = 0.8, confidence_mod = 0.3
        # adjusted = 1.0 + (0.8 - 1.0) * 0.3 = 0.94
        # result = 1000 * 0.94 = 940
        assert result < 1000.0
        assert result == pytest.approx(940.0)

    def test_low_confidence_minimizes_adjustment(self):
        """confidence=20 → multiplier close to 1.0 regardless of bias."""
        pe = PhaseEvidence(
            phase=WyckoffPhase.MARKUP,
            composite_score=75.0,
            confidence=20.0,
            position_bias="long",
        )
        result = adjust_position_for_phase(1000.0, pe)
        # multiplier = 1.2, confidence_mod = 0.2
        # adjusted = 1.0 + (1.2 - 1.0) * 0.2 = 1.04
        # result = 1000 * 1.04 = 1040
        assert result == pytest.approx(1040.0)
        # Should be close to original (within 10%)
        assert abs(result - 1000.0) < 100.0

    def test_no_evidence_no_change(self):
        """phase_evidence=None → size unchanged."""
        result = adjust_position_for_phase(1000.0, None)
        assert result == 1000.0

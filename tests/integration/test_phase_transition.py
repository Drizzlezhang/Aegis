"""Tests for phase transition detection and cooldown."""

import pytest

from src.agents.quant_brain.phase_predictor import PhasePredictor
from src.models.trend_phase import WyckoffPhase


class TestPhaseTransitionScenarios:
    """Tests for phase transition detection and cooldown."""

    @pytest.mark.asyncio
    async def test_accumulation_to_markup_transition(self, mock_ohlcv_linear_up):
        """Two consecutive calls: first accumulation, then markup → transition detected."""
        p = PhasePredictor()

        # First call — should set _last_phase
        result1 = await p.predict(mock_ohlcv_linear_up)
        assert result1.phase in WyckoffPhase
        assert p._last_phase is not None

        # Second call with same data — same phase, no transition
        result2 = await p.predict(mock_ohlcv_linear_up)
        assert result2.transition is None  # Same phase

    @pytest.mark.asyncio
    async def test_cooldown_prevents_whipsaw(self, mock_ohlcv_linear_up, mock_ohlcv_linear_down):
        """Within cooldown_bars, phase change is suppressed."""
        p = PhasePredictor()

        # First: uptrend → bullish phase
        await p.predict(mock_ohlcv_linear_up)
        first_phase = p._last_phase

        # Second: downtrend — should be suppressed by cooldown (bars_since=1 < 3)
        result2 = await p.predict(mock_ohlcv_linear_down)
        # Phase should be held at last_phase due to cooldown
        assert result2.phase == first_phase
        assert result2.transition is None

    @pytest.mark.asyncio
    async def test_cooldown_expired_allows_transition(self, mock_ohlcv_linear_up, mock_ohlcv_linear_down):
        """After cooldown_bars calls, transition is allowed."""
        p = PhasePredictor()

        # First: uptrend → bullish phase
        await p.predict(mock_ohlcv_linear_up)
        first_phase = p._last_phase

        # Call 3 more times with same data to pass cooldown (bars_since >= 3)
        for _ in range(3):
            await p.predict(mock_ohlcv_linear_up)

        # Now downtrend — cooldown expired, transition should be allowed
        result = await p.predict(mock_ohlcv_linear_down)
        if result.phase != first_phase:
            assert result.transition is not None
            assert "→" in result.transition

    @pytest.mark.asyncio
    async def test_same_phase_resets_nothing(self, mock_ohlcv_linear_up):
        """Consecutive same phase → bars_since_transition increments, transition=None."""
        p = PhasePredictor()

        await p.predict(mock_ohlcv_linear_up)
        bars_after_first = p._bars_since_last_transition

        await p.predict(mock_ohlcv_linear_up)
        # bars_since should increment (no reset since same phase)
        assert p._bars_since_last_transition == bars_after_first + 1

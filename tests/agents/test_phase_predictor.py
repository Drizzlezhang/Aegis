"""Unit tests for PhasePredictor — 7-dimension Wyckoff phase engine."""

import asyncio

import pytest

from src.agents.quant_brain.phase_predictor import PhasePredictor
from src.config import PhaseConfig, PhaseThresholds
from src.models.scoring import MacroRegime
from src.models.trend_phase import DimensionScore, TrendPhaseResult, WyckoffPhase


def _closes(bars):
    return [b.close for b in bars]


def _volumes(bars):
    return [b.volume for b in bars]


class TestPhasePredictorBasics:
    """Basic sanity checks for PhasePredictor."""

    def test_predict_returns_trend_phase_result(self, mock_ohlcv_linear_up):
        """predict() returns TrendPhaseResult with valid fields."""
        p = PhasePredictor()
        result = asyncio.run(p.predict(mock_ohlcv_linear_up))
        assert isinstance(result, TrendPhaseResult)
        assert result.phase in WyckoffPhase
        assert 0 <= result.composite_score <= 100
        assert 0 <= result.confidence <= 1

    def test_predict_returns_7_dimension_scores(self, mock_ohlcv_linear_up):
        """7-dim engine returns exactly 7 DimensionScores."""
        p = PhasePredictor()
        result = asyncio.run(p.predict(mock_ohlcv_linear_up))
        assert len(result.dimension_scores) == 7
        dim_names = {d.name for d in result.dimension_scores}
        assert dim_names == {
            "trend_momentum", "velocity", "acceleration",
            "volume", "mean_reversion", "macro", "valuation",
        }

    def test_weights_sum_to_one(self):
        """Default weights sum to 1.0."""
        p = PhasePredictor()
        assert abs(sum(p._weights.values()) - 1.0) < 0.001


class TestDimensionScoring:
    """Individual dimension scorer tests."""

    def test_trend_momentum_bullish_on_uptrend(self, mock_ohlcv_linear_up):
        """Uptrend → trend_momentum > 50."""
        p = PhasePredictor()
        score = p._score_trend_momentum(_closes(mock_ohlcv_linear_up))
        assert score.normalized_score > 50

    def test_trend_momentum_bearish_on_downtrend(self, mock_ohlcv_linear_down):
        """Downtrend → trend_momentum < 50."""
        p = PhasePredictor()
        score = p._score_trend_momentum(_closes(mock_ohlcv_linear_down))
        assert score.normalized_score < 50

    def test_volume_score_range(self, mock_ohlcv_linear_up):
        """Volume score is within [0, 100]."""
        p = PhasePredictor()
        score = p._score_volume(_closes(mock_ohlcv_linear_up), _volumes(mock_ohlcv_linear_up))
        assert 0 <= score.normalized_score <= 100

    def test_mean_reversion_neutral_on_volatile(self, mock_ohlcv_volatile):
        """Volatile/sideways → mean_reversion score is valid (0-100)."""
        p = PhasePredictor()
        score = p._score_mean_reversion(_closes(mock_ohlcv_volatile))
        assert 0 <= score.normalized_score <= 100

    def test_macro_score_with_none_regime(self):
        """macro_regime=None → score = 50 (neutral)."""
        p = PhasePredictor()
        score = p._score_macro(None)
        assert score.normalized_score == 50.0

    def test_velocity_positive_on_uptrend(self, mock_ohlcv_linear_up):
        """Linear uptrend → velocity > 50."""
        p = PhasePredictor()
        score = p._score_velocity(mock_ohlcv_linear_up)
        assert score.normalized_score > 50

    def test_velocity_negative_on_downtrend(self, mock_ohlcv_linear_down):
        """Linear downtrend → velocity < 50."""
        p = PhasePredictor()
        score = p._score_velocity(mock_ohlcv_linear_down)
        assert score.normalized_score < 50

    def test_acceleration_neutral_on_linear(self, mock_ohlcv_linear_up):
        """Linear (constant velocity) → acceleration ≈ 50."""
        p = PhasePredictor()
        score = p._score_acceleration(mock_ohlcv_linear_up)
        assert 35 <= score.normalized_score <= 65

    def test_acceleration_positive_on_exponential(self, mock_ohlcv_exponential_up):
        """Exponential (accelerating) → acceleration > 50."""
        p = PhasePredictor()
        score = p._score_acceleration(mock_ohlcv_exponential_up)
        assert score.normalized_score > 50


class TestPhaseDetermination:
    """Wyckoff phase classification logic."""

    def test_determine_phase_markup(self):
        """composite > 70, volume > 60 → Markup."""
        p = PhasePredictor()
        phase, conf = p._determine_phase(75.0, 65.0, True)
        assert phase == WyckoffPhase.MARKUP
        assert conf >= 0.7

    def test_determine_phase_markdown(self):
        """composite < 30, volume > 60 → Markdown."""
        p = PhasePredictor()
        phase, conf = p._determine_phase(25.0, 65.0, False)
        assert phase == WyckoffPhase.MARKDOWN
        assert conf >= 0.7

    def test_determine_phase_re_accumulation(self):
        """composite > 60, volume <= 60 → Re-Accumulation."""
        p = PhasePredictor()
        phase, conf = p._determine_phase(65.0, 45.0, True)
        assert phase == WyckoffPhase.RE_ACCUMULATION

    def test_determine_phase_re_distribution(self):
        """composite < 40, volume <= 60 → Re-Distribution."""
        p = PhasePredictor()
        phase, conf = p._determine_phase(35.0, 45.0, False)
        assert phase == WyckoffPhase.RE_DISTRIBUTION

    def test_determine_phase_accumulation(self):
        """40 <= composite <= 60, trend_rising → Accumulation."""
        p = PhasePredictor()
        phase, conf = p._determine_phase(50.0, 50.0, True)
        assert phase == WyckoffPhase.ACCUMULATION

    def test_determine_phase_distribution(self):
        """40 <= composite <= 60, NOT trend_rising → Distribution."""
        p = PhasePredictor()
        phase, conf = p._determine_phase(50.0, 50.0, False)
        assert phase == WyckoffPhase.DISTRIBUTION


class TestLowVolatility:
    """Low-volatility override tests."""

    def test_low_volatility_triggers_override(self, mock_ohlcv_flat):
        """Extremely flat data triggers low_volatility_override."""
        p = PhasePredictor()
        result = asyncio.run(p.predict(mock_ohlcv_flat))
        assert result.low_volatility_override is True
        assert result.composite_score == 50.0
        assert "Low volatility" in result.phase_description

    def test_normal_volatility_no_override(self, mock_ohlcv_volatile):
        """Normal volatility does NOT trigger override."""
        p = PhasePredictor()
        result = asyncio.run(p.predict(mock_ohlcv_volatile))
        assert result.low_volatility_override is False


class TestConfigOverride:
    """Config-driven behaviour tests."""

    def test_custom_weights_override(self, mock_ohlcv_linear_up):
        """Custom 5-dim weights (no velocity/acceleration) still works."""
        custom_weights = {
            "trend_momentum": 0.30,
            "volume": 0.30,
            "mean_reversion": 0.20,
            "macro": 0.10,
            "valuation": 0.10,
        }
        p = PhasePredictor(weights=custom_weights)
        result = asyncio.run(p.predict(mock_ohlcv_linear_up))
        assert len(result.dimension_scores) == 5
        assert isinstance(result, TrendPhaseResult)

    def test_custom_thresholds(self, mock_ohlcv_linear_up):
        """Extremely high markup_threshold prevents Markup classification."""
        cfg = PhaseConfig(thresholds=PhaseThresholds(markup_threshold=95.0))
        p = PhasePredictor(config=cfg)
        result = asyncio.run(p.predict(mock_ohlcv_linear_up))
        assert result.phase != WyckoffPhase.MARKUP

    def test_disabled_config(self):
        """enabled=False returns disabled result immediately."""
        cfg = PhaseConfig(enabled=False)
        p = PhasePredictor(config=cfg)
        result = asyncio.run(p.predict([]))
        assert result.phase_description == "Phase predictor disabled"
        assert result.composite_score == 50.0


class TestInsufficientData:
    """Graceful handling of insufficient data."""

    def test_insufficient_data_returns_neutral(self, mock_ohlcv_short):
        """Data < min_ohlcv_bars → neutral result."""
        p = PhasePredictor()
        result = asyncio.run(p.predict(mock_ohlcv_short))
        assert result.composite_score == 50.0
        assert result.confidence == 0.0
        assert "Insufficient data" in result.phase_description

    def test_empty_data_returns_neutral(self):
        """Empty list → neutral result."""
        p = PhasePredictor()
        result = asyncio.run(p.predict([]))
        assert result.composite_score == 50.0


class TestBoundaryValues:
    """Edge case and boundary tests."""

    def test_all_scores_clipped_to_0_100(self, mock_ohlcv_linear_up):
        """Every dimension score is clipped to [0, 100]."""
        p = PhasePredictor()
        result = asyncio.run(p.predict(mock_ohlcv_linear_up))
        for d in result.dimension_scores:
            assert 0 <= d.normalized_score <= 100, f"{d.name} out of range"
            assert 0 <= d.weighted_score <= 100, f"{d.name} weighted out of range"
            assert 0 <= d.weight <= 1, f"{d.name} weight out of range"

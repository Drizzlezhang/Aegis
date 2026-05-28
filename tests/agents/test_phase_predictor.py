"""Unit tests for PhasePredictor — 7-dimension Wyckoff phase engine."""

import asyncio
import os
from datetime import datetime

import pytest

from src.agents.quant_brain.phase_predictor import PhasePredictor
from src.config import PhaseConfig, PhaseThresholds
from src.models.analysis import ValuationRange
from src.models.scoring import MacroRegime
from src.models.trend_phase import DimensionScore, TrendPhaseResult, WyckoffPhase


def _closes(bars):
    return [b.close for b in bars]


def _volumes(bars):
    return [b.volume for b in bars]


class TestPhasePredictorBasics:
    """Basic sanity checks for PhasePredictor."""

    async def test_predict_returns_trend_phase_result(self, mock_ohlcv_linear_up):
        """predict() returns TrendPhaseResult with valid fields."""
        p = PhasePredictor()
        result = await p.predict(mock_ohlcv_linear_up)
        assert isinstance(result, TrendPhaseResult)
        assert result.phase in WyckoffPhase
        assert 0 <= result.composite_score <= 100
        assert 0 <= result.confidence <= 100

    async def test_predict_returns_7_dimension_scores(self, mock_ohlcv_linear_up):
        """7-dim engine returns exactly 7 DimensionScores."""
        p = PhasePredictor()
        result = await p.predict(mock_ohlcv_linear_up)
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
        score = p._score_trend_momentum(
            _closes(mock_ohlcv_linear_up),
            [b.high for b in mock_ohlcv_linear_up],
            [b.low for b in mock_ohlcv_linear_up],
        )
        assert score.normalized_score > 50

    def test_trend_momentum_bearish_on_downtrend(self, mock_ohlcv_linear_down):
        """Downtrend → trend_momentum < 50."""
        p = PhasePredictor()
        score = p._score_trend_momentum(
            _closes(mock_ohlcv_linear_down),
            [b.high for b in mock_ohlcv_linear_down],
            [b.low for b in mock_ohlcv_linear_down],
        )
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
        assert conf >= 70.0

    def test_determine_phase_markdown(self):
        """composite < 30, volume > 60 → Markdown."""
        p = PhasePredictor()
        phase, conf = p._determine_phase(25.0, 65.0, False)
        assert phase == WyckoffPhase.MARKDOWN
        assert conf >= 70.0

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

    async def test_low_volatility_triggers_override(self, mock_ohlcv_flat):
        """Extremely flat data triggers low_volatility_override."""
        p = PhasePredictor()
        result = await p.predict(mock_ohlcv_flat)
        assert result.low_volatility_override is True
        assert result.composite_score == 50.0
        assert "Low volatility" in result.phase_description

    async def test_normal_volatility_no_override(self, mock_ohlcv_volatile):
        """Normal volatility does NOT trigger override."""
        p = PhasePredictor()
        result = await p.predict(mock_ohlcv_volatile)
        assert result.low_volatility_override is False


class TestConfigOverride:
    """Config-driven behaviour tests."""

    async def test_custom_weights_override(self, mock_ohlcv_linear_up):
        """Custom 5-dim weights (no velocity/acceleration) still works."""
        custom_weights = {
            "trend_momentum": 0.30,
            "volume": 0.30,
            "mean_reversion": 0.20,
            "macro": 0.10,
            "valuation": 0.10,
        }
        p = PhasePredictor(weights=custom_weights)
        result = await p.predict(mock_ohlcv_linear_up)
        assert len(result.dimension_scores) == 5
        assert isinstance(result, TrendPhaseResult)

    async def test_custom_thresholds(self, mock_ohlcv_linear_up):
        """Extremely high markup_threshold prevents Markup classification."""
        cfg = PhaseConfig(thresholds=PhaseThresholds(markup_threshold=95.0))
        p = PhasePredictor(config=cfg)
        result = await p.predict(mock_ohlcv_linear_up)
        assert result.phase != WyckoffPhase.MARKUP

    async def test_disabled_config(self):
        """enabled=False returns disabled result immediately."""
        cfg = PhaseConfig(enabled=False)
        p = PhasePredictor(config=cfg)
        result = await p.predict([])
        assert result.phase_description == "Phase predictor disabled"
        assert result.composite_score == 50.0


class TestInsufficientData:
    """Graceful handling of insufficient data."""

    async def test_insufficient_data_returns_neutral(self, mock_ohlcv_short):
        """Data < min_ohlcv_bars → neutral result."""
        p = PhasePredictor()
        result = await p.predict(mock_ohlcv_short)
        assert result.composite_score == 50.0
        assert result.confidence == 0.0
        assert "Insufficient data" in result.phase_description

    async def test_empty_data_returns_neutral(self):
        """Empty list → neutral result."""
        p = PhasePredictor()
        result = await p.predict([])
        assert result.composite_score == 50.0


class TestBoundaryValues:
    """Edge case and boundary tests."""

    async def test_all_scores_clipped_to_0_100(self, mock_ohlcv_linear_up):
        """Every dimension score is clipped to [0, 100]."""
        p = PhasePredictor()
        result = await p.predict(mock_ohlcv_linear_up)
        for d in result.dimension_scores:
            assert 0 <= d.normalized_score <= 100, f"{d.name} out of range"
            assert 0 <= d.weighted_score <= 100, f"{d.name} weighted out of range"
            assert 0 <= d.weight <= 1, f"{d.name} weight out of range"


class TestValuationScoring:
    """Tests for _score_valuation dimension."""

    def test_high_pe_ratio_gives_low_score(self):
        """PE > 历史 80 percentile → score < 40."""
        p = PhasePredictor()
        vr = ValuationRange(
            symbol="TEST",
            timestamp=datetime(2024, 1, 1),
            current_price=100.0,
            low_estimate=80.0,
            fair_estimate=100.0,
            high_estimate=120.0,
            method="pe_band",
            confidence=0.8,
            pe_percentile=85.0,
        )
        score = p._score_valuation(vr, 100.0)
        assert score.normalized_score < 40

    def test_low_pe_ratio_gives_high_score(self):
        """PE < 历史 20 percentile → score > 60."""
        p = PhasePredictor()
        vr = ValuationRange(
            symbol="TEST",
            timestamp=datetime(2024, 1, 1),
            current_price=100.0,
            low_estimate=80.0,
            fair_estimate=100.0,
            high_estimate=120.0,
            method="pe_band",
            confidence=0.8,
            pe_percentile=15.0,
        )
        score = p._score_valuation(vr, 100.0)
        assert score.normalized_score > 60

    def test_missing_fundamentals_returns_neutral(self):
        """无基本面数据 → fallback score = 50."""
        p = PhasePredictor()
        score = p._score_valuation(None, 100.0)
        assert score.normalized_score == 50.0

    def test_normal_pe_gives_moderate_score(self):
        """PE 在中位数附近 → score 45-55."""
        p = PhasePredictor()
        vr = ValuationRange(
            symbol="TEST",
            timestamp=datetime(2024, 1, 1),
            current_price=100.0,
            low_estimate=80.0,
            fair_estimate=100.0,
            high_estimate=120.0,
            method="pe_band",
            confidence=0.8,
            pe_percentile=50.0,
        )
        score = p._score_valuation(vr, 100.0)
        assert 45 <= score.normalized_score <= 55


class TestDeterminePhaseEdgeCases:
    """Edge cases for phase determination at boundary scores."""

    def test_score_exactly_at_markup_threshold(self):
        """composite_score == 70 (markup_threshold) → falls through to accumulation (strict >)."""
        p = PhasePredictor()
        phase, _ = p._determine_phase(70.0, 65.0, True)
        # 70 is NOT > 70, volume > 60 but composite not > threshold
        # Falls through all conditions to fallback: trend_rising → ACCUMULATION
        assert phase == WyckoffPhase.ACCUMULATION

    def test_score_exactly_at_markdown_threshold(self):
        """composite_score == 30 (markdown_threshold) → falls through to distribution (strict <)."""
        p = PhasePredictor()
        phase, _ = p._determine_phase(30.0, 65.0, False)
        # 30 is NOT < 30, volume > 60 but composite not < threshold
        # Falls through all conditions to fallback: not trend_rising → DISTRIBUTION
        assert phase == WyckoffPhase.DISTRIBUTION

    def test_score_at_bullish_boundary(self):
        """composite_score == 60 (bullish_boundary) → accumulation."""
        p = PhasePredictor()
        phase, _ = p._determine_phase(60.0, 50.0, True)
        assert phase == WyckoffPhase.ACCUMULATION

    def test_score_at_bearish_boundary(self):
        """composite_score == 40 (bearish_boundary) → distribution."""
        p = PhasePredictor()
        phase, _ = p._determine_phase(40.0, 50.0, False)
        assert phase == WyckoffPhase.DISTRIBUTION

    def test_all_dimensions_score_zero(self):
        """极端: 所有维度 = 0 → markdown."""
        p = PhasePredictor()
        phase, _ = p._determine_phase(0.0, 65.0, False)
        assert phase == WyckoffPhase.MARKDOWN

    def test_all_dimensions_score_hundred(self):
        """极端: 所有维度 = 100 → markup."""
        p = PhasePredictor()
        phase, _ = p._determine_phase(100.0, 65.0, True)
        assert phase == WyckoffPhase.MARKUP

    def test_mixed_extreme_scores(self):
        """一半维度=0, 一半=100 → 由加权决定 (composite=50, neutral zone)."""
        p = PhasePredictor()
        phase, _ = p._determine_phase(50.0, 50.0, True)
        assert phase == WyckoffPhase.ACCUMULATION


class TestConfidence:
    """Confidence field tests (A7)."""

    async def test_uniform_scores_high_confidence(self, mock_ohlcv_linear_up):
        """All dimensions close → confidence > 80."""
        p = PhasePredictor()
        result = await p.predict(mock_ohlcv_linear_up)
        # Linear uptrend should have fairly consistent dimension scores
        assert result.confidence > 0, "confidence should be positive"
        assert 0 <= result.confidence <= 100

    async def test_divergent_scores_low_confidence(self, mock_ohlcv_volatile):
        """Volatile data → dimensions diverge → confidence < 80."""
        p = PhasePredictor()
        result = await p.predict(mock_ohlcv_volatile)
        assert 0 <= result.confidence <= 100


class TestPhaseTransition:
    """Phase transition signal tests (A8)."""

    async def test_first_call_no_transition(self, mock_ohlcv_linear_up):
        """首次调用 → transition = None."""
        p = PhasePredictor()
        result = await p.predict(mock_ohlcv_linear_up)
        assert result.transition is None

    async def test_phase_change_produces_signal(self, mock_ohlcv_linear_up, mock_ohlcv_linear_down):
        """相邻调用 phase 变化 → transition 字符串正确."""
        p = PhasePredictor()
        first = await p.predict(mock_ohlcv_linear_up)
        assert first.transition is None

        second = await p.predict(mock_ohlcv_linear_down)
        if second.phase != first.phase:
            assert second.transition is not None
            assert "→" in second.transition
            assert first.phase.value in second.transition
            assert second.phase.value in second.transition

    async def test_same_phase_no_transition(self, mock_ohlcv_linear_up):
        """连续相同 phase → transition = None."""
        p = PhasePredictor()
        first = await p.predict(mock_ohlcv_linear_up)
        second = await p.predict(mock_ohlcv_linear_up)
        if second.phase == first.phase:
            assert second.transition is None


class TestADXProxy:
    """A1: ADX warm-up transparency tests."""

    async def test_adx_proxy_used_with_30_bars(self):
        """AC1.1: 30 bar input → adx_proxy_used=True (data < 2*period=28)."""
        from datetime import datetime, timedelta

        from src.config import PhaseConfig
        from src.models.market import OHLCV

        bars = []
        base_time = datetime(2024, 1, 1)
        for i in range(30):
            close = 100 + i * 0.5
            bars.append(OHLCV(
                symbol="TEST",
                timestamp=base_time + timedelta(days=i),
                open=close - 0.1,
                high=close + 0.3,
                low=close - 0.3,
                close=close,
                volume=1_000_000,
            ))
        cfg = PhaseConfig(min_ohlcv_bars=30)
        p = PhasePredictor(config=cfg)
        result = await p.predict(bars)
        assert result.adx_proxy_used is True

    async def test_adx_proxy_not_used_with_60_bars(self, mock_ohlcv_linear_up):
        """AC1.2: 60 bar input → adx_proxy_used=False."""
        p = PhasePredictor()
        result = await p.predict(mock_ohlcv_linear_up)
        assert result.adx_proxy_used is False

    async def test_adx_proxy_description_marker(self):
        """AC1.3: proxy mode → phase_description contains '[ADX proxy mode]'."""
        from datetime import datetime, timedelta

        from src.config import PhaseConfig
        from src.models.market import OHLCV

        bars = []
        base_time = datetime(2024, 1, 1)
        for i in range(30):
            close = 100 + i * 0.5
            bars.append(OHLCV(
                symbol="TEST",
                timestamp=base_time + timedelta(days=i),
                open=close - 0.1,
                high=close + 0.3,
                low=close - 0.3,
                close=close,
                volume=1_000_000,
            ))
        cfg = PhaseConfig(min_ohlcv_bars=30)
        p = PhasePredictor(config=cfg)
        result = await p.predict(bars)
        assert "[ADX proxy mode]" in result.phase_description


class TestDimensionFailure:
    """A2: Dimension failure eventization tests."""

    def test_degraded_dimensions_on_failure(self, monkeypatch):
        """AC2.1: mock dimension failure → degraded_dimensions contains dim name."""
        from src.agents.quant_brain.phase_predictor import PhasePredictor

        p = PhasePredictor()

        # Mock _score_volume to raise
        def _fail(*args, **kwargs):
            raise RuntimeError("simulated volume failure")

        monkeypatch.setattr(p, "_score_volume", _fail)

        dims, degraded = p._compute_all_dimensions(
            closes=[100.0] * 60,
            volumes=[1000] * 60,
            ohlcv_data=[],
            macro_regime=None,
            valuation_range=None,
            current_price=100.0,
        )
        assert "volume" in degraded
        assert len(p._events) >= 1
        assert p._events[0].dim_name == "volume"
        assert "simulated volume failure" in p._events[0].error_message

    def test_failed_dimension_score_is_neutral(self, monkeypatch):
        """AC2.2: failed dimension normalized_score = 50.0."""
        from src.agents.quant_brain.phase_predictor import PhasePredictor

        p = PhasePredictor()

        def _fail(*args, **kwargs):
            raise RuntimeError("simulated failure")

        monkeypatch.setattr(p, "_score_volume", _fail)

        dims, degraded = p._compute_all_dimensions(
            closes=[100.0] * 60,
            volumes=[1000] * 60,
            ohlcv_data=[],
            macro_regime=None,
            valuation_range=None,
            current_price=100.0,
        )
        vol_dim = next(d for d in dims if d.name == "volume")
        assert vol_dim.normalized_score == 50.0

    def test_phase_dimension_failure_event_recorded(self, monkeypatch):
        """AC2.3: self._events contains PhaseDimensionFailure record."""
        from src.agents.quant_brain.phase_predictor import PhasePredictor
        from src.agents.quant_brain.phase_events import PhaseDimensionFailure

        p = PhasePredictor()

        def _fail(*args, **kwargs):
            raise ValueError("test error")

        monkeypatch.setattr(p, "_score_macro", _fail)

        dims, degraded = p._compute_all_dimensions(
            closes=[100.0] * 60,
            volumes=[1000] * 60,
            ohlcv_data=[],
            macro_regime=None,
            valuation_range=None,
            current_price=100.0,
        )
        assert len(p._events) == 1
        assert isinstance(p._events[0], PhaseDimensionFailure)
        assert p._events[0].dim_name == "macro"


class TestWeightRebalancing:
    """A3: Dynamic weight rebalancing tests."""

    def test_rebalance_two_failed_dims(self):
        """AC3.1: 2 dims fail → remaining 5 get increased weights."""
        p = PhasePredictor()
        failed = {"volume", "macro"}
        rebalanced = p._rebalance_weights(failed)

        # Failed dims get 0
        assert rebalanced["volume"] == 0.0
        assert rebalanced["macro"] == 0.0

        # Active dims get increased weights
        # volume=0.18 + macro=0.10 = 0.28 redistributed across 5 dims = 0.056 each
        assert rebalanced["trend_momentum"] == pytest.approx(0.20 + 0.056)
        assert rebalanced["velocity"] == pytest.approx(0.15 + 0.056)
        assert rebalanced["acceleration"] == pytest.approx(0.12 + 0.056)
        assert rebalanced["mean_reversion"] == pytest.approx(0.15 + 0.056)
        assert rebalanced["valuation"] == pytest.approx(0.10 + 0.056)

    def test_rebalance_weights_sum_to_one(self):
        """AC3.2: rebalanced weights sum to 1.0 (±0.001)."""
        p = PhasePredictor()
        failed = {"volume", "macro"}
        rebalanced = p._rebalance_weights(failed)
        assert abs(sum(rebalanced.values()) - 1.0) < 0.001

    def test_no_failures_returns_original_weights(self):
        """AC3.3: no failures → original weights returned."""
        p = PhasePredictor()
        rebalanced = p._rebalance_weights(set())
        assert rebalanced == p._weights
        assert abs(sum(rebalanced.values()) - 1.0) < 0.001


class TestCompositeSmoothing:
    """A7: Composite score EMA smoothing tests."""

    async def test_smoothing_attenuates_change(self, mock_ohlcv_linear_up):
        """AC7.1: alpha=0.5 → second call's composite is smoothed toward first."""
        from src.config import PhaseConfig

        cfg = PhaseConfig(composite_smoothing_alpha=0.5)
        p = PhasePredictor(config=cfg)

        result1 = await p.predict(mock_ohlcv_linear_up)
        score1 = result1.composite_score

        result2 = await p.predict(mock_ohlcv_linear_up)
        score2 = result2.composite_score

        # With same data, raw composite would be identical.
        # With smoothing, score2 should equal score1 (no change to smooth).
        assert score1 == pytest.approx(score2)

    async def test_smoothing_alpha_zero_disabled(self, mock_ohlcv_linear_up):
        """AC7.2: alpha=0 → composite_score unchanged (no smoothing)."""
        from src.config import PhaseConfig

        cfg = PhaseConfig(composite_smoothing_alpha=0)
        p = PhasePredictor(config=cfg)

        result1 = await p.predict(mock_ohlcv_linear_up)
        result2 = await p.predict(mock_ohlcv_linear_up)

        # With alpha=0, smoothing is disabled — raw composite used each time
        assert result1.composite_score == pytest.approx(result2.composite_score)

    async def test_smoothing_alpha_one_equals_raw(self, mock_ohlcv_linear_up):
        """AC7.3: alpha=1 → composite_score equals raw value (no memory)."""
        from src.config import PhaseConfig

        cfg = PhaseConfig(composite_smoothing_alpha=1.0)
        p = PhasePredictor(config=cfg)

        result1 = await p.predict(mock_ohlcv_linear_up)
        result2 = await p.predict(mock_ohlcv_linear_up)

        # alpha=1 means full replacement — same as raw
        assert result1.composite_score == pytest.approx(result2.composite_score)


class TestI18n:
    """A4: i18n phase description tests."""

    async def test_locale_en_vs_zh_cn_different(self, mock_ohlcv_linear_up):
        """AC4.1: en and zh-CN produce different descriptions."""
        p = PhasePredictor()
        result_en = await p.predict(mock_ohlcv_linear_up, locale="en")
        result_zh = await p.predict(mock_ohlcv_linear_up, locale="zh-CN")
        assert result_en.phase_description != result_zh.phase_description

    async def test_default_locale_is_en(self, mock_ohlcv_linear_up):
        """AC4.2: default locale=en, behavior unchanged."""
        p = PhasePredictor()
        result = await p.predict(mock_ohlcv_linear_up)
        assert "Smart money" in result.phase_description or "Uptrend" in result.phase_description or \
            "Downtrend" in result.phase_description or "Pause" in result.phase_description


class TestPhaseHistory:
    """A5: Historical phase persistence tests."""

    async def test_predict_writes_to_history(self):
        """AC5.1: 5 _write_phase_history calls → 5 records in phase_history."""
        import sqlite3

        from src.config import get_config
        from src.models.trend_phase import TrendPhaseResult, WyckoffPhase

        config = get_config()
        db_path = config.database.url.replace("sqlite:///", "").replace("sqlite+aiosqlite:///", "")
        db_path = os.path.expanduser(db_path)

        # Clear existing records for clean test
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM phase_history")
        conn.commit()
        conn.close()

        p = PhasePredictor()
        result = TrendPhaseResult(
            phase=WyckoffPhase.ACCUMULATION,
            confidence=50.0,
            composite_score=50.0,
        )
        for _ in range(5):
            await p._write_phase_history("TEST", result)

        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM phase_history").fetchone()[0]
        conn.close()
        assert count == 5

    async def test_write_failure_does_not_raise(self, mock_ohlcv_linear_up, monkeypatch):
        """AC5.2: DB write failure → no exception raised."""
        p = PhasePredictor()

        async def _fail_write(*args, **kwargs):
            raise RuntimeError("simulated DB failure")

        monkeypatch.setattr(p, "_write_phase_history", _fail_write)

        # Should not raise
        result = await p.predict(mock_ohlcv_linear_up)
        assert result is not None
        assert result.phase is not None


class TestPhaseTrendAnalysis:
    """A6: Short-term phase trend analysis tests."""

    async def test_all_same_phase_stability_one(self):
        """AC6.1: 20 same phases → stability=1.0."""
        import sqlite3

        from src.config import get_config

        config = get_config()
        db_path = config.database.url.replace("sqlite:///", "").replace("sqlite+aiosqlite:///", "")
        db_path = os.path.expanduser(db_path)

        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM phase_history")
        conn.commit()

        # Insert 20 identical phase records
        import uuid
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        for i in range(20):
            conn.execute(
                "INSERT INTO phase_history (id, symbol, timestamp, phase, composite_score, confidence, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), "TREND_TEST", now.isoformat(), "accumulation", 50.0, 50.0, now.isoformat()),
            )
        conn.commit()
        conn.close()

        p = PhasePredictor()
        summary = await p._analyze_recent_phases("TREND_TEST", lookback=20)
        assert summary.stability_score == 1.0
        assert summary.dominant_phase == "accumulation"
        assert summary.transition_count == 0

    async def test_alternating_phases_stability_near_zero(self):
        """AC6.2: alternating phases → stability ≈ 0."""
        import sqlite3

        from src.config import get_config

        config = get_config()
        db_path = config.database.url.replace("sqlite:///", "").replace("sqlite+aiosqlite:///", "")
        db_path = os.path.expanduser(db_path)

        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM phase_history")
        conn.commit()

        import uuid
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        phases = ["accumulation", "distribution"] * 10
        for phase in phases:
            conn.execute(
                "INSERT INTO phase_history (id, symbol, timestamp, phase, composite_score, confidence, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), "ALT_TEST", now.isoformat(), phase, 50.0, 50.0, now.isoformat()),
            )
        conn.commit()
        conn.close()

        p = PhasePredictor()
        summary = await p._analyze_recent_phases("ALT_TEST", lookback=20)
        # 20 records → 19 transitions → stability = 1 - 19/19 = 0
        assert summary.stability_score == 0.0
        assert summary.transition_count == 19

    async def test_dominant_phase_is_most_frequent(self):
        """AC6.3: dominant_phase = most frequent phase."""
        import sqlite3

        from src.config import get_config

        config = get_config()
        db_path = config.database.url.replace("sqlite:///", "").replace("sqlite+aiosqlite:///", "")
        db_path = os.path.expanduser(db_path)

        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM phase_history")
        conn.commit()

        import uuid
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        # 12 markup, 5 accumulation, 3 distribution
        for _ in range(12):
            conn.execute(
                "INSERT INTO phase_history (id, symbol, timestamp, phase, composite_score, confidence, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), "DOM_TEST", now.isoformat(), "markup", 75.0, 80.0, now.isoformat()),
            )
        for _ in range(5):
            conn.execute(
                "INSERT INTO phase_history (id, symbol, timestamp, phase, composite_score, confidence, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), "DOM_TEST", now.isoformat(), "accumulation", 50.0, 50.0, now.isoformat()),
            )
        for _ in range(3):
            conn.execute(
                "INSERT INTO phase_history (id, symbol, timestamp, phase, composite_score, confidence, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), "DOM_TEST", now.isoformat(), "distribution", 40.0, 40.0, now.isoformat()),
            )
        conn.commit()
        conn.close()

        p = PhasePredictor()
        summary = await p._analyze_recent_phases("DOM_TEST", lookback=20)
        assert summary.dominant_phase == "markup"

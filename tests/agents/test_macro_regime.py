"""Tests for MacroRegimeAnalyzer."""

import pytest

from src.agents.quant_brain.macro_regime import MacroRegimeAnalyzer
from src.models import MacroRegime


class TestRegimeRiskOn:
    @pytest.mark.asyncio
    async def test_vix_low_plus_bullish_trend(self):
        """VIX < 15 + SPY/QQQ bullish → risk_on."""
        analyzer = MacroRegimeAnalyzer()
        result = await analyzer.analyze({
            "VIX": 12.0,
            "SPY_trend": "bullish",
            "QQQ_trend": "bullish",
        })
        assert result.regime == "risk_on"
        assert result.vix_signal == "low"
        assert result.market_trend == "bullish"
        assert result.factors["vix"] == 0.3
        assert result.factors["trend"] == 0.3

    @pytest.mark.asyncio
    async def test_all_factors_risk_on(self):
        """All 5 factors risk_on → highest score."""
        analyzer = MacroRegimeAnalyzer()
        result = await analyzer.analyze({
            "VIX": 10.0,
            "SPY_trend": "bullish",
            "QQQ_trend": "bullish",
            "XLK_XLY_ratio": 1.5,
            "TLT_change_pct": -1.0,
            "GLD_change_pct": -0.5,
            "HYG_LQD_change": 0.02,
        })
        assert result.regime == "risk_on"
        assert result.confidence > 0.7


class TestRegimeRiskOff:
    @pytest.mark.asyncio
    async def test_vix_high_plus_safe_haven_rally(self):
        """VIX > 30 + TLT/GLD both up → risk_off."""
        analyzer = MacroRegimeAnalyzer()
        result = await analyzer.analyze({
            "VIX": 35.0,
            "SPY_trend": "bearish",
            "QQQ_trend": "bearish",
            "TLT_change_pct": 2.0,
            "GLD_change_pct": 1.5,
        })
        assert result.regime == "risk_off"
        assert result.vix_signal == "extreme"
        assert result.factors["vix"] == -0.5
        assert result.factors["safe_haven"] == -0.2

    @pytest.mark.asyncio
    async def test_all_factors_risk_off(self):
        analyzer = MacroRegimeAnalyzer()
        result = await analyzer.analyze({
            "VIX": 32.0,
            "SPY_trend": "bearish",
            "QQQ_trend": "bearish",
            "XLP_XLU_ratio": 1.5,
            "TLT_change_pct": 1.0,
            "GLD_change_pct": 0.5,
            "HYG_LQD_change": -0.03,
        })
        assert result.regime == "risk_off"
        assert result.confidence > 0.7


class TestRegimeNeutral:
    @pytest.mark.asyncio
    async def test_all_factors_neutral(self):
        """No data → neutral."""
        analyzer = MacroRegimeAnalyzer()
        result = await analyzer.analyze({})
        assert result.regime == "neutral"

    @pytest.mark.asyncio
    async def test_mixed_signals_neutral(self):
        """Mixed signals cancel out → neutral."""
        analyzer = MacroRegimeAnalyzer()
        result = await analyzer.analyze({
            "VIX": 12.0,  # risk_on (+0.3)
            "SPY_trend": "bearish",  # risk_off (-0.3)
            "QQQ_trend": "bearish",
        })
        assert result.regime == "neutral"

    @pytest.mark.asyncio
    async def test_vix_normal_plus_neutral_trend(self):
        analyzer = MacroRegimeAnalyzer()
        result = await analyzer.analyze({
            "VIX": 18.0,
            "SPY_trend": "neutral",
            "QQQ_trend": "neutral",
        })
        assert result.regime == "neutral"


class TestGracefulDegradation:
    @pytest.mark.asyncio
    async def test_no_crash_with_partial_data(self):
        """Partial data → no exception."""
        analyzer = MacroRegimeAnalyzer()
        result = await analyzer.analyze({"VIX": 15.0})
        assert isinstance(result, MacroRegime)
        assert result.regime in ("risk_on", "risk_off", "neutral")

    @pytest.mark.asyncio
    async def test_no_crash_with_none_values(self):
        """None values in data → no exception."""
        analyzer = MacroRegimeAnalyzer()
        result = await analyzer.analyze({
            "VIX": None,
            "SPY_trend": None,
            "QQQ_trend": None,
            "TLT_change_pct": None,
            "GLD_change_pct": None,
        })
        assert isinstance(result, MacroRegime)
        assert result.regime == "neutral"

    @pytest.mark.asyncio
    async def test_no_crash_with_empty_dict(self):
        """Empty dict → no exception, returns neutral."""
        analyzer = MacroRegimeAnalyzer()
        result = await analyzer.analyze({})
        assert isinstance(result, MacroRegime)
        assert result.regime == "neutral"


class TestVIXSignals:
    @pytest.mark.asyncio
    async def test_vix_low(self):
        analyzer = MacroRegimeAnalyzer()
        result = await analyzer.analyze({"VIX": 12.0})
        assert result.vix_signal == "low"
        assert result.factors["vix"] == 0.3

    @pytest.mark.asyncio
    async def test_vix_normal(self):
        analyzer = MacroRegimeAnalyzer()
        result = await analyzer.analyze({"VIX": 18.0})
        assert result.vix_signal == "normal"
        assert result.factors["vix"] == 0.0

    @pytest.mark.asyncio
    async def test_vix_elevated(self):
        analyzer = MacroRegimeAnalyzer()
        result = await analyzer.analyze({"VIX": 25.0})
        assert result.vix_signal == "elevated"
        assert result.factors["vix"] == -0.3

    @pytest.mark.asyncio
    async def test_vix_extreme(self):
        analyzer = MacroRegimeAnalyzer()
        result = await analyzer.analyze({"VIX": 35.0})
        assert result.vix_signal == "extreme"
        assert result.factors["vix"] == -0.5


class TestConfidence:
    @pytest.mark.asyncio
    async def test_risk_on_confidence_above_0_5(self):
        analyzer = MacroRegimeAnalyzer()
        result = await analyzer.analyze({
            "VIX": 10.0, "SPY_trend": "bullish",
        })
        assert result.confidence > 0.5

    @pytest.mark.asyncio
    async def test_risk_off_confidence_above_0_5(self):
        analyzer = MacroRegimeAnalyzer()
        result = await analyzer.analyze({
            "VIX": 35.0, "SPY_trend": "bearish",
        })
        assert result.confidence > 0.5

    @pytest.mark.asyncio
    async def test_neutral_confidence_is_moderate(self):
        analyzer = MacroRegimeAnalyzer()
        result = await analyzer.analyze({})
        assert 0.3 <= result.confidence <= 0.7

    @pytest.mark.asyncio
    async def test_confidence_not_exceed_1(self):
        analyzer = MacroRegimeAnalyzer()
        result = await analyzer.analyze({
            "VIX": 8.0, "SPY_trend": "bullish", "QQQ_trend": "bullish",
            "XLK_XLY_ratio": 2.0, "TLT_change_pct": -2.0,
            "GLD_change_pct": -2.0, "HYG_LQD_change": 0.05,
        })
        assert result.confidence <= 1.0
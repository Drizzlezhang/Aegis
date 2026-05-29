"""Tests for TechnicalScorerSkill."""

import pytest

from src.models import TechnicalScoreBreakdown


class TestTechnicalScoreBreakdown:
    def test_total_calculation(self):
        score = TechnicalScoreBreakdown(
            trend_score=25, deviation_score=15, volume_score=12,
            support_score=10, macd_score=13, rsi_score=10,
            adx_score=8, obv_score=7,
        )
        assert score.total == 100.0

    def test_all_zero(self):
        score = TechnicalScoreBreakdown(
            trend_score=0, deviation_score=0, volume_score=0,
            support_score=0, macd_score=0, rsi_score=0,
            adx_score=0, obv_score=0,
        )
        assert score.total == 0.0
        assert score.grade == "F"

    def test_grade_a(self):
        score = TechnicalScoreBreakdown(
            trend_score=25, deviation_score=15, volume_score=12,
            support_score=10, macd_score=13, rsi_score=10,
            adx_score=8, obv_score=7,
        )
        assert score.grade == "A"

    def test_grade_b(self):
        score = TechnicalScoreBreakdown(
            trend_score=20, deviation_score=12, volume_score=10,
            support_score=10, macd_score=8, rsi_score=5,
            adx_score=3, obv_score=2,
        )
        assert score.total == 70.0
        assert score.grade == "B"

    def test_grade_c(self):
        score = TechnicalScoreBreakdown(
            trend_score=15, deviation_score=10, volume_score=8,
            support_score=5, macd_score=7, rsi_score=5,
            adx_score=2, obv_score=1,
        )
        assert score.total == 53.0
        assert score.grade == "C"

    def test_grade_d(self):
        score = TechnicalScoreBreakdown(
            trend_score=10, deviation_score=8, volume_score=5,
            support_score=5, macd_score=5, rsi_score=5,
            adx_score=1, obv_score=1,
        )
        assert score.total == 40.0
        assert score.grade == "D"

    def test_grade_f(self):
        score = TechnicalScoreBreakdown(
            trend_score=5, deviation_score=5, volume_score=4,
            support_score=0, macd_score=4, rsi_score=3,
            adx_score=1, obv_score=1,
        )
        assert score.total == 23.0
        assert score.grade == "F"

    def test_grade_boundary_80_is_a(self):
        score = TechnicalScoreBreakdown(
            trend_score=25, deviation_score=15, volume_score=12,
            support_score=10, macd_score=10, rsi_score=0,
            adx_score=5, obv_score=3,
        )
        assert score.total == 80.0
        assert score.grade == "A"

    def test_grade_boundary_65_is_b(self):
        score = TechnicalScoreBreakdown(
            trend_score=25, deviation_score=15, volume_score=12,
            support_score=5, macd_score=5, rsi_score=0,
            adx_score=2, obv_score=1,
        )
        assert score.total == 65.0
        assert score.grade == "B"


class TestTechnicalScorerTrend:
    @pytest.mark.asyncio
    async def test_full_trend_bullish(self):
        """SMA50 > SMA200 + Price > SMA50 → trend=25."""
        from skills.algorithms.technical_scorer.skill import TechnicalScorerSkill

        skill = TechnicalScorerSkill()
        indicators = {
            "sma50": 200, "sma200": 180, "close": 210, "adx": 30,
        }
        params = {
            "ohlcv_data": [],
            "technical_indicators": indicators,
            "support_levels": [],
            "current_price": 210,
        }
        result = await skill.execute(params)
        assert result.success
        assert result.data.trend_score == 25.0
        assert result.data.adx_score == 6.0
        assert result.data.total > 0

    @pytest.mark.asyncio
    async def test_trend_zero_when_empty_indicators(self):
        from skills.algorithms.technical_scorer.skill import TechnicalScorerSkill

        skill = TechnicalScorerSkill()
        result = await skill.execute({
            "ohlcv_data": [],
            "technical_indicators": {},
            "support_levels": [],
            "current_price": 100,
        })
        assert result.success
        assert isinstance(result.data, TechnicalScoreBreakdown)
        assert result.data.trend_score == 0.0


class TestTechnicalScorerDeviation:
    @pytest.mark.asyncio
    async def test_perfect_deviation_zero_pct(self):
        """价格 = SMA50，偏离 0% → 满分 15."""
        from skills.algorithms.technical_scorer.skill import TechnicalScorerSkill

        skill = TechnicalScorerSkill()
        indicators = {"sma50": 100, "close": 100}
        result = await skill.execute({
            "ohlcv_data": [],
            "technical_indicators": indicators,
            "support_levels": [],
            "current_price": 100,
        })
        assert result.success
        assert result.data.deviation_score == 15.0

    @pytest.mark.asyncio
    async def test_extreme_deviation_above_10pct(self):
        """偏离 > 10% → 0 分."""
        from skills.algorithms.technical_scorer.skill import TechnicalScorerSkill

        skill = TechnicalScorerSkill()
        indicators = {"sma50": 100, "close": 115}
        result = await skill.execute({
            "ohlcv_data": [],
            "technical_indicators": indicators,
            "support_levels": [],
            "current_price": 115,
        })
        assert result.success
        assert result.data.deviation_score == 0.0

    @pytest.mark.asyncio
    async def test_no_sma50_zero_deviation(self):
        from skills.algorithms.technical_scorer.skill import TechnicalScorerSkill

        skill = TechnicalScorerSkill()
        result = await skill.execute({
            "ohlcv_data": [],
            "technical_indicators": {},
            "support_levels": [],
            "current_price": 100,
        })
        assert result.success
        assert result.data.deviation_score == 0.0


class TestTechnicalScorerRSI:
    @pytest.mark.asyncio
    async def test_rsi_oversold_bounce_30_45(self):
        """RSI 在 30-45 (超卖反弹) → 满分 10."""
        from skills.algorithms.technical_scorer.skill import TechnicalScorerSkill

        skill = TechnicalScorerSkill()
        indicators = {"rsi": 35}
        result = await skill.execute({
            "ohlcv_data": [],
            "technical_indicators": indicators,
            "support_levels": [],
            "current_price": 100,
        })
        assert result.success
        assert result.data.rsi_score == 10.0

    @pytest.mark.asyncio
    async def test_rsi_healthy_30_to_70(self):
        """RSI 30-70 健康区间 → 5 分."""
        from skills.algorithms.technical_scorer.skill import TechnicalScorerSkill

        skill = TechnicalScorerSkill()
        indicators = {"rsi": 55}
        result = await skill.execute({
            "ohlcv_data": [],
            "technical_indicators": indicators,
            "support_levels": [],
            "current_price": 100,
        })
        assert result.success
        assert result.data.rsi_score == 5.0

    @pytest.mark.asyncio
    async def test_rsi_overbought_above_70(self):
        """RSI > 70 超买 → 2 分."""
        from skills.algorithms.technical_scorer.skill import TechnicalScorerSkill

        skill = TechnicalScorerSkill()
        indicators = {"rsi": 75}
        result = await skill.execute({
            "ohlcv_data": [],
            "technical_indicators": indicators,
            "support_levels": [],
            "current_price": 100,
        })
        assert result.success
        assert result.data.rsi_score == 2.0

    @pytest.mark.asyncio
    async def test_rsi_oversold_below_30(self):
        """RSI < 30 超卖危险 → 3 分."""
        from skills.algorithms.technical_scorer.skill import TechnicalScorerSkill

        skill = TechnicalScorerSkill()
        indicators = {"rsi": 25}
        result = await skill.execute({
            "ohlcv_data": [],
            "technical_indicators": indicators,
            "support_levels": [],
            "current_price": 100,
        })
        assert result.success
        assert result.data.rsi_score == 3.0


class TestTechnicalScorerFullScore:
    @pytest.mark.asyncio
    async def test_max_score_scenario(self):
        """All best conditions → 100, Grade A."""
        from skills.algorithms.technical_scorer.skill import TechnicalScorerSkill

        skill = TechnicalScorerSkill()
        indicators = {
            "sma50": 200, "sma200": 180, "close": 210, "adx": 40,
            "relative_volume": 2.0,
            "obv_aligned": True, "obv_trend": "up", "sma50_above_sma200": True,
            "macd": 1.5, "macd_signal": 1.0, "macd_histogram_expanding": True,
            "rsi": 35,
        }
        indicators["close"] = 202
        params = {
            "ohlcv_data": [],
            "technical_indicators": indicators,
            "support_levels": [197.0],  # nearest support <3% from 202 → 10
            "current_price": 202,
        }
        result = await skill.execute(params)
        assert result.success
        assert result.data.total == pytest.approx(100.0, abs=1.0)
        assert result.data.grade == "A"

"""100-point technical scoring algorithm skill."""

import logging
from typing import Any

from src.models import TechnicalScoreBreakdown
from src.skills.base import BaseSkill, SkillResult, SkillType

logger = logging.getLogger(__name__)


class TechnicalScorerSkill(BaseSkill):
    """100-point technical scoring algorithm skill.

    Scoring breakdown:
      - Trend (0-25): SMA50>SMA200 +15, Price>SMA50 +10
      - Deviation (0-15): 0% within [-2%,+2%] → 15, >±10% → 0
      - Volume (0-12): relative_volume > 1.5 +12
      - Support (0-10): nearest support <3% +10, 3-5% +5, >5% 0
      - MACD (0-13): MACD>Signal +7, histogram expanding +6
      - RSI (0-10): 30-45 +10, 30-70 +5, >70 +2, <30 +3
      - ADX (0-8): trend strength scoring
      - OBV (0-7): volume-price alignment scoring
    """

    @property
    def skill_type(self) -> SkillType:
        return SkillType.ALGORITHM

    @property
    def description(self) -> str:
        return "100-point technical scoring algorithm"

    @property
    def version(self) -> str:
        return "0.1.0"

    def get_required_params(self) -> list[str]:
        return ["ohlcv_data", "technical_indicators", "support_levels", "current_price"]

    def _score_trend(self, indicators: dict) -> float:
        score = 0.0
        sma50 = indicators.get("sma50", 0)
        sma200 = indicators.get("sma200", 0)
        price = indicators.get("close", 0)

        if sma50 > 0 and sma200 > 0 and sma50 > sma200:
            score += 15
        if price > 0 and sma50 > 0 and price > sma50:
            score += 10

        return score

    def _score_deviation(self, indicators: dict) -> float:
        sma50 = indicators.get("sma50", 0)
        price = indicators.get("close", 0)
        if sma50 <= 0 or price <= 0:
            return 0.0

        deviation_pct = abs(price - sma50) / sma50
        max_score = self.config.get("deviation_score_max", 15)

        if deviation_pct <= 0.02:
            return float(max_score)
        if deviation_pct >= 0.10:
            return 0.0
        return float(max_score) * (1 - (deviation_pct - 0.02) / 0.08)

    def _score_volume(self, indicators: dict) -> float:
        rel_vol = indicators.get("relative_volume", 0)
        return 12.0 if rel_vol > 1.5 else 0.0

    def _score_support(self, support_levels: list[float], current_price: float) -> float:
        if not support_levels or current_price <= 0:
            return 0.0

        nearest_support = max(s for s in support_levels if s < current_price) if any(
            s < current_price for s in support_levels
        ) else None

        if nearest_support is None:
            return 0.0

        distance_pct = (current_price - nearest_support) / current_price

        if distance_pct < 0.03:
            return 10.0
        if distance_pct < 0.05:
            return 5.0
        return 0.0

    def _score_macd(self, indicators: dict) -> float:
        score = 0.0
        macd = indicators.get("macd", 0)
        macd_signal = indicators.get("macd_signal", 0)
        histogram_expanding = indicators.get("macd_histogram_expanding", False)

        if macd > macd_signal:
            score += 7
        if histogram_expanding:
            score += 6

        return score

    def _score_rsi(self, indicators: dict) -> float:
        rsi = indicators.get("rsi", 50)

        if 30 <= rsi <= 45:
            return 10.0
        if 30 <= rsi <= 70:
            return 5.0
        if rsi > 70:
            return 2.0
        if rsi < 30:
            return 3.0
        return 0.0

    def _score_adx(self, indicators: dict) -> float:
        adx = indicators.get("adx", 0)
        if adx >= 40:
            return 8.0
        if adx >= 25:
            return 6.0
        if adx >= 20:
            return 3.0
        return 1.0

    def _score_obv(self, indicators: dict) -> float:
        obv_trend = indicators.get("obv_trend")
        price_trend = indicators.get("sma50_above_sma200")
        obv_aligned = indicators.get("obv_aligned")

        if obv_trend == "up" and price_trend:
            return 7.0
        if obv_trend == "up" or price_trend or obv_aligned is True:
            return 4.0
        if obv_trend == "down" and price_trend is False:
            return 1.0
        return 3.0

    async def execute(self, params: dict[str, Any]) -> SkillResult:
        try:
            ohlcv_data: list = params.get("ohlcv_data", [])
            indicators: dict = params.get("technical_indicators", {})
            support_levels: list[float] = params.get("support_levels", [])
            current_price: float = params.get("current_price", 0.0)

            trend_score = self._score_trend(indicators)
            deviation_score = self._score_deviation(indicators)
            volume_score = self._score_volume(indicators)
            support_score = self._score_support(support_levels, current_price)
            macd_score = self._score_macd(indicators)
            rsi_score = self._score_rsi(indicators)
            adx_score = self._score_adx(indicators)
            obv_score = self._score_obv(indicators)

            score = TechnicalScoreBreakdown(
                trend_score=min(trend_score, 25),
                deviation_score=min(deviation_score, 15),
                volume_score=min(volume_score, 12),
                support_score=min(support_score, 10),
                macd_score=min(macd_score, 13),
                rsi_score=min(rsi_score, 10),
                adx_score=min(adx_score, 8),
                obv_score=min(obv_score, 7),
            )

            return SkillResult.success_result(score, {"grade": score.grade, "total": score.total})

        except Exception as e:
            logger.error(f"Technical scoring failed: {e}")
            return SkillResult.error_result(f"Technical scoring failed: {e}")
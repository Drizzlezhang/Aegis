"""宏观 Regime 多因子判断器。"""

import logging
from typing import Any

from src.models import MacroRegime

logger = logging.getLogger(__name__)

FACTOR_NAMES = ["vix", "trend", "sector", "safe_haven", "credit"]


class MacroRegimeAnalyzer:
    """宏观 Regime 判断器。

    5 因子加权判断 risk_on / risk_off / neutral。
    综合得分 > 0.2 → risk_on，< -0.2 → risk_off，其他 → neutral。
    """

    def _score_vix(self, vix: float | None) -> tuple[float, str]:
        if vix is None:
            return 0.0, "normal"
        if vix < 15:
            return 0.3, "low"
        if vix <= 20:
            return 0.0, "normal"
        if vix <= 30:
            return -0.3, "elevated"
        return -0.5, "extreme"

    def _score_trend(self, spy_trend: str | None, qqq_trend: str | None) -> tuple[float, str]:
        trend_signals = [spy_trend, qqq_trend]
        bullish = sum(1 for t in trend_signals if t == "bullish")
        bearish = sum(1 for t in trend_signals if t == "bearish")

        if bullish > bearish:
            return 0.3, "bullish"
        if bearish > bullish:
            return -0.3, "bearish"
        return 0.0, "neutral"

    def _score_sector(
        self,
        growth_ratio: float | None,
        defensive_ratio: float | None,
    ) -> tuple[float, str]:
        score = 0.0
        rotation = "balanced"

        if growth_ratio is not None and growth_ratio > 1:
            score += 0.2
            rotation = "growth"
        elif defensive_ratio is not None and defensive_ratio > 1:
            score -= 0.2
            rotation = "defensive"

        return score, rotation

    def _score_safe_haven(
        self,
        tlt_change: float | None,
        gld_change: float | None,
    ) -> tuple[float, float]:
        pressure = 0.0
        score = 0.0

        if tlt_change is not None:
            pressure += 0.5 if tlt_change > 0 else 0
        if gld_change is not None:
            pressure += 0.5 if gld_change > 0 else 0

        absent = 0
        if tlt_change is not None:
            absent += 1
        if gld_change is not None:
            absent += 1

        if absent == 0:
            return 0.0, 0.0

        pressure = pressure / absent  # normalize to 0-1

        if tlt_change is not None and gld_change is not None:
            if tlt_change > 0 and gld_change > 0:
                score = -0.2
            elif tlt_change < 0 and gld_change < 0:
                score = 0.1

        return score, pressure

    def _score_credit(self, hyg_lqd_change: float | None) -> tuple[float, str]:
        if hyg_lqd_change is None:
            return 0.0, "normal"
        if hyg_lqd_change > 0:
            return 0.1, "tight"
        if hyg_lqd_change < 0:
            return -0.2, "wide"
        return 0.0, "normal"

    async def analyze(self, market_data: dict[str, Any]) -> MacroRegime:
        factors: dict[str, float] = {}
        confidence = 0.5

        vix = market_data.get("VIX")
        vix_score, vix_signal = self._score_vix(vix)
        factors["vix"] = vix_score

        trend_score, market_trend = self._score_trend(
            market_data.get("SPY_trend"), market_data.get("QQQ_trend")
        )
        factors["trend"] = trend_score

        sector_score, sector_rotation = self._score_sector(
            market_data.get("XLK_XLY_ratio"), market_data.get("XLP_XLU_ratio")
        )
        factors["sector"] = sector_score

        haven_score, haven_pressure = self._score_safe_haven(
            market_data.get("TLT_change_pct"), market_data.get("GLD_change_pct")
        )
        factors["safe_haven"] = haven_score

        credit_score, credit_spread = self._score_credit(market_data.get("HYG_LQD_change"))
        factors["credit"] = credit_score

        total = sum(factors.values())

        if total > 0.2:
            regime = "risk_on"
            confidence = min(0.5 + abs(total) * 0.5, 1.0)
        elif total < -0.2:
            regime = "risk_off"
            confidence = min(0.5 + abs(total) * 0.5, 1.0)
        else:
            regime = "neutral"
            confidence = max(0.3, 0.5 - abs(total))

        return MacroRegime(
            regime=regime,
            confidence=round(confidence, 2),
            vix_signal=vix_signal,
            market_trend=market_trend,
            sector_rotation=sector_rotation,
            safe_haven_pressure=round(haven_pressure, 2),
            credit_spread=credit_spread,
            factors=factors,
        )
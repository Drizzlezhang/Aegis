"""Bull/Bear 研究员 — 辩论系统的两方论点生成。"""

import logging

from src.models import AgentState
from src.models.debate import DebateArgument, DebateRole

logger = logging.getLogger(__name__)


class BullResearcher:
    """多头研究员：寻找看多理由。纯规则引擎，不调用 LLM。"""

    async def argue(self, state: AgentState) -> DebateArgument:
        evidence: list[str] = []
        risks: list[str] = []
        confidence = 0.5
        points_count = 0

        # 1. 技术评分
        grade = self._extract_grade(state)
        if grade in ("A", "B"):
            points_count += 1
            evidence.append(f"技术评分 grade={grade}，技术面健康")
            confidence += 0.12
        elif grade == "C":
            points_count += 1
            evidence.append(f"技术评分 grade={grade}，技术面中性")
            confidence += 0.05
        else:
            risks.append(f"技术评分 grade={grade}，技术面偏弱")

        # 2. 估值
        if state.valuation_range and getattr(state.valuation_range, "is_undervalued", False):
            points_count += 1
            discount = getattr(state.valuation_range, "discount_to_fair", 0)
            evidence.append(f"估值低于 fair value，discount={discount:.1f}%")
            confidence += 0.15
        else:
            risks.append("估值不低于 fair value")

        # 3. 支撑位
        if state.support_levels and len(state.support_levels) > 0:
            points_count += 1
            prices = [s.price for s in state.support_levels]
            evidence.append(f"存在 {len(state.support_levels)} 个支撑位: {prices}")
            confidence += 0.08

        # 4. 宏观 Regime
        regime = self._extract_regime(state)
        if regime == "risk_on":
            points_count += 1
            evidence.append("宏观 Regime=risk_on，环境支持")
            confidence += 0.1
        elif regime == "risk_off":
            risks.append("宏观 Regime=risk_off，系统性风险")
            confidence -= 0.1

        # 5. 推荐策略
        if state.recommended_options and len(state.recommended_options) > 0:
            points_count += 1
            count = len(state.recommended_options)
            evidence.append(f"存在 {count} 个推荐策略，多策略共振")
            confidence += 0.05 * min(count, 3)

        confidence = max(0.1, min(1.0, confidence))

        return DebateArgument(
            role=DebateRole.BULL,
            position="bullish",
            key_points=evidence,
            confidence=round(confidence, 2),
            evidence=evidence,
            risks=risks,
        )

    def _extract_grade(self, state: AgentState) -> str:
        report = state.analysis_report or ""
        for line in report.split("\n"):
            if "Grade:" in line and "Total:" in line:
                parts = line.split("Grade:")[1].split(",")[0].strip()
                return parts
        return "F"

    def _extract_regime(self, state: AgentState) -> str:
        report = state.analysis_report or ""
        for line in report.split("\n"):
            if "Regime:" in line:
                parts = line.split("Regime:")[1].split("(")[0].strip()
                return parts
        return "neutral"


class BearResearcher:
    """空头研究员：寻找看空理由。纯规则引擎，不调用 LLM。"""

    async def argue(self, state: AgentState) -> DebateArgument:
        evidence: list[str] = []
        risks: list[str] = []
        confidence = 0.5
        points_count = 0

        # 1. 技术评分
        grade = self._extract_grade(state)
        if grade in ("D", "F"):
            points_count += 1
            evidence.append(f"技术评分 grade={grade}，技术面恶化")
            confidence += 0.15
        elif grade == "C":
            confidence += 0.03

        # 2. RSI 超买
        report = state.analysis_report or ""
        for line in report.split("\n"):
            if "RSI:" in line:
                try:
                    rsi_part = line.split("RSI:")[1].split("/")[0].strip()
                    rsi_val = float(rsi_part)
                    if rsi_val > 70:
                        points_count += 1
                        evidence.append(f"RSI={rsi_val:.0f}，超买风险")
                        confidence += 0.12
                    elif rsi_val > 65:
                        evidence.append(f"RSI={rsi_val:.0f}，偏高")
                        confidence += 0.03
                except (ValueError, IndexError):
                    pass
                break

        # 3. VIX elevated/high
        if state.market_indices:
            for idx in state.market_indices:
                sym = idx.symbol.upper()
                if sym in ("^VIX", "VIX"):
                    vix = idx.price
                    if vix > 30:
                        points_count += 1
                        evidence.append(f"VIX={vix:.0f}，极端波动率")
                        confidence += 0.15
                    elif vix > 20:
                        points_count += 1
                        evidence.append(f"VIX={vix:.0f}，波动率偏高")
                        confidence += 0.08
                    break

        # 4. 宏观 Regime
        regime = self._extract_regime(state)
        if regime == "risk_off":
            points_count += 1
            evidence.append("宏观 Regime=risk_off，系统性风险")
            confidence += 0.15
        elif regime == "risk_on":
            risks.append("宏观 Regime=risk_on，不利于看空")
            confidence -= 0.05

        # 5. 估值过高
        if state.valuation_range and getattr(state.valuation_range, "is_overvalued", False):
            points_count += 1
            premium = getattr(state.valuation_range, "premium_to_fair", 0)
            evidence.append(f"估值高于 fair value，premium={premium:.1f}%")
            confidence += 0.1

        confidence = max(0.1, min(1.0, confidence))

        return DebateArgument(
            role=DebateRole.BEAR,
            position="bearish",
            key_points=evidence,
            confidence=round(confidence, 2),
            evidence=evidence,
            risks=risks,
        )

    def _extract_grade(self, state: AgentState) -> str:
        report = state.analysis_report or ""
        for line in report.split("\n"):
            if "Grade:" in line and "Total:" in line:
                parts = line.split("Grade:")[1].split(",")[0].strip()
                return parts
        return "F"

    def _extract_regime(self, state: AgentState) -> str:
        report = state.analysis_report or ""
        for line in report.split("\n"):
            if "Regime:" in line:
                parts = line.split("Regime:")[1].split("(")[0].strip()
                return parts
        return "neutral"
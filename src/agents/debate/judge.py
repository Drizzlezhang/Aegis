"""InvestmentJudge — 辩论仲裁。纯规则引擎。"""

from src.models.debate import (
    DebateArgument,
    JudgeVerdict,
    InvestmentRating,
)

POSITIVE_KEYWORDS = ["估值便宜", "估值低于"]
NEGATIVE_KEYWORDS = ["系统性风险", "risk_off", "估值过高"]


class InvestmentJudge:
    """投资辩论仲裁者。纯规则引擎，不调用 LLM。"""

    async def evaluate(
        self,
        bull: DebateArgument,
        bear: DebateArgument,
        symbol: str,
    ) -> JudgeVerdict:
        delta = bull.confidence - bear.confidence

        # Bonus/penalty
        for kw in POSITIVE_KEYWORDS:
            if any(kw in point for point in bull.key_points):
                delta += 0.1
                break

        for kw in NEGATIVE_KEYWORDS:
            if any(kw in point for point in bear.key_points):
                delta -= 0.15
                break

        # 高质量辩论 bonus
        if len(bull.key_points) >= 3 and len(bear.key_points) >= 3:
            delta *= 1.1

        if delta > 0.3:
            rating = InvestmentRating.STRONG_BUY
            winning_side = "bull"
        elif delta > 0.1:
            rating = InvestmentRating.BUY
            winning_side = "bull"
        elif delta > -0.1:
            rating = InvestmentRating.HOLD
            winning_side = "neutral"
        elif delta > -0.3:
            rating = InvestmentRating.SELL
            winning_side = "bear"
        else:
            rating = InvestmentRating.STRONG_SELL
            winning_side = "bear"

        confidence = min(0.5 + abs(delta) * 0.5, 1.0)

        key_factors = list(bull.key_points[:3]) + list(bear.key_points[:3])
        dissenting = bear.key_points[:2] if winning_side == "bull" else bull.key_points[:2]

        reasoning = (
            f"{symbol} debate: Bull confidence={bull.confidence:.2f}, "
            f"Bear confidence={bear.confidence:.2f}, delta={delta:.2f}. "
            f"Verdict: {rating.value}, winning side: {winning_side}."
        )

        action_items: list[str] = []
        if rating in (InvestmentRating.STRONG_BUY, InvestmentRating.BUY):
            action_items.append("Consider entering position with proper sizing")
            action_items.append("Set stop-loss at nearest support level")
        elif rating in (InvestmentRating.SELL, InvestmentRating.STRONG_SELL):
            action_items.append("Consider reducing or exiting position")
            action_items.append("Review risk exposure")

        return JudgeVerdict(
            rating=rating,
            confidence=round(confidence, 2),
            winning_side=winning_side,
            reasoning=reasoning,
            key_factors=key_factors,
            action_items=action_items,
            dissenting_points=dissenting,
        )
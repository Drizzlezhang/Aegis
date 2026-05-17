"""InvestmentJudge — 辩论仲裁。纯规则引擎。"""

from src.models.debate import (
    DebateArgument,
    DebateRound,
    JudgeVerdict,
    InvestmentRating,
)

POSITIVE_KEYWORDS = ["估值便宜", "估值低于"]
NEGATIVE_KEYWORDS = ["系统性风险", "risk_off", "估值过高"]


class InvestmentJudge:
    """投资辩论仲裁者。纯规则引擎，不调用 LLM。"""

    async def evaluate_rounds(
        self,
        rounds: list[DebateRound],
        symbol: str,
    ) -> JudgeVerdict:
        if not rounds:
            raise ValueError("rounds must not be empty")
        if len(rounds) == 1:
            return await self.evaluate(rounds[0].bull_argument, rounds[0].bear_argument, symbol)

        scores = self._score_debate_quality(rounds)
        return self._derive_verdict(scores, rounds, symbol)

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

    def _score_debate_quality(self, rounds: list[DebateRound]) -> dict[str, float]:
        bull_scores = [r.bull_argument.confidence for r in rounds if r.bull_argument]
        bear_scores = [r.bear_argument.confidence for r in rounds if r.bear_argument]
        return {
            "bull_avg_confidence": sum(bull_scores) / len(bull_scores),
            "bear_avg_confidence": sum(bear_scores) / len(bear_scores),
            "bull_trend": bull_scores[-1] - bull_scores[0],
            "bear_trend": bear_scores[-1] - bear_scores[0],
            "rounds_played": float(len(rounds)),
        }

    def _derive_verdict(self, scores: dict[str, float], rounds: list[DebateRound], symbol: str) -> JudgeVerdict:
        final_round = rounds[-1]
        bull = final_round.bull_argument
        bear = final_round.bear_argument
        delta = (
            scores["bull_avg_confidence"]
            + scores["bull_trend"] * 0.2
            - scores["bear_avg_confidence"]
            - scores["bear_trend"] * 0.2
        )

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

        confidence = min(max(0.5 + abs(delta) * 0.5, max(scores["bull_avg_confidence"], scores["bear_avg_confidence"]) * 0.8), 0.95)
        key_factors = list(bull.key_points[:3]) + list(bear.key_points[:3])
        dissenting = bear.key_points[:2] if winning_side == "bull" else bull.key_points[:2]

        return JudgeVerdict(
            rating=rating,
            confidence=round(confidence, 2),
            winning_side=winning_side,
            reasoning=(
                f"{symbol} debate after {int(scores['rounds_played'])} rounds: "
                f"bull_avg={scores['bull_avg_confidence']:.2f}, "
                f"bear_avg={scores['bear_avg_confidence']:.2f}, delta={delta:.2f}. "
                f"Verdict: {rating.value}, winning side: {winning_side}."
            ),
            key_factors=key_factors,
            action_items=self._action_items_for_rating(rating),
            dissenting_points=dissenting,
        )

    def _action_items_for_rating(self, rating: InvestmentRating) -> list[str]:
        if rating in (InvestmentRating.STRONG_BUY, InvestmentRating.BUY):
            return ["Consider entering position with proper sizing", "Set stop-loss at nearest support level"]
        if rating in (InvestmentRating.SELL, InvestmentRating.STRONG_SELL):
            return ["Consider reducing or exiting position", "Review risk exposure"]
        return []

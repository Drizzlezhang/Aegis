"""左侧抄底 LEAPS Call 策略。"""

from __future__ import annotations

import logging
from typing import Any

from src.models import RecommendedOption, SupportResistanceLevel

from ..market_context import StrategyMarketContext
from .base import StrategyGenerator

logger = logging.getLogger(__name__)


class LeftSideLeapsStrategy(StrategyGenerator):
    """左侧抄底 LEAPS Call 策略。

    多因子支撑交汇 + 估值便宜 + IV 低时入场。
    入场条件需满足 ≥ 3/5。
    """

    name = "left_side_leaps"

    def generate(  # noqa: C901
        self,
        symbol: str,
        options_chain: Any,
        support_levels: list[SupportResistanceLevel],
        resistance_levels: list[SupportResistanceLevel],
        valuation_range: Any | None,
        current_price: float,
        market_context: StrategyMarketContext | None = None,
    ) -> RecommendedOption | None:
        try:
            conditions_met = 0
            conditions_total = 5

            # 条件 1: 价格接近支撑位（距离 < 3%）
            near_support = False
            if support_levels and current_price > 0:
                nearest_support = min(
                    (s for s in support_levels if s.price < current_price),
                    key=lambda s: current_price - s.price,
                    default=None,
                )
                if nearest_support is not None:
                    distance_pct = (current_price - nearest_support.price) / current_price
                    if distance_pct < 0.03:
                        near_support = True
                        conditions_met += 1

            # 条件 2: 估值低于 fair value
            is_undervalued = (
                valuation_range is not None and getattr(valuation_range, "is_undervalued", False)
            )
            if is_undervalued:
                conditions_met += 1

            # 条件 3: IV Rank < 50（期权便宜）
            iv_low = False
            if options_chain:
                iv_rank = getattr(options_chain, "iv_rank", None)
                if iv_rank is not None and iv_rank < 50:
                    iv_low = True
                    conditions_met += 1

            # 条件 4: 技术评分 Grade >= C（从 market_context 推断）
            grade_ok = False
            if market_context and hasattr(market_context, "technical_grade"):
                grade = market_context.technical_grade
                if grade and grade not in ("D", "F"):
                    grade_ok = True
            if grade_ok:
                conditions_met += 1

            # 条件 5: 宏观 Regime 不是 risk_off
            regime_ok = False
            if market_context and hasattr(market_context, "macro_regime"):
                if market_context.macro_regime and market_context.macro_regime != "risk_off":
                    regime_ok = True
            if regime_ok:
                conditions_met += 1

            if conditions_met < 3:
                logger.info(
                    f"LeftSideLeaps for {symbol}: {conditions_met}/{conditions_total} conditions met, "
                    f"need >= 3, skipping"
                )
                return None

            leaps_calls = [
                c
                for c in options_chain.calls
                if c.is_leaps and c.delta and 0.6 <= c.delta <= 0.8
            ]
            if not leaps_calls:
                logger.warning(f"No suitable LEAPS Call options for {symbol}")
                return None

            leaps_calls.sort(key=lambda c: abs(c.delta - 0.7) if c.delta else float("inf"))
            best_call = leaps_calls[0]
            entry_price = best_call.mid_price or best_call.last_price or 0.0
            if entry_price <= 0:
                return None

            entry_support = (
                max(support_levels, key=lambda level: level.confidence) if support_levels else None
            )
            target_price = entry_price * 2.0 if entry_support else None

            stop_loss = entry_price * 0.5 if entry_price > 0 else None

            risk_reward_ratio = None
            if target_price and stop_loss:
                potential_gain = target_price - entry_price
                max_loss = entry_price - stop_loss
                if max_loss > 0:
                    risk_reward_ratio = potential_gain / max_loss

            confidence = 0.55
            if entry_support:
                confidence += entry_support.confidence * 0.25
            if is_undervalued:
                confidence += 0.1
            if iv_low:
                confidence += 0.05
            confidence = max(0.1, min(1.0, confidence))

            reasoning = f"Left-Side LEAPS Call for {symbol}:\n"
            reasoning += f"  • Conditions met: {conditions_met}/{conditions_total}\n"
            reasoning += f"  • Support convergence: {'Yes' if near_support else 'No'}\n"
            reasoning += f"  • Undervalued: {'Yes' if is_undervalued else 'No'}\n"
            reasoning += f"  • IV low: {'Yes' if iv_low else 'No'}\n"
            reasoning += "  • Entry: 3 tranches (40%+30%+30%)\n"
            reasoning += f"  • Strike: {best_call.strike:.2f}, Expiry: {best_call.expiry}\n"
            reasoning += f"  • Delta: {best_call.delta:.2f}\n"
            if risk_reward_ratio:
                reasoning += f"  • Risk/Reward: {risk_reward_ratio:.2f}\n"

            return RecommendedOption(
                contract=best_call,
                recommendation_type=self.name,
                entry_price=entry_price,
                target_price=target_price,
                stop_loss=stop_loss,
                risk_reward_ratio=risk_reward_ratio,
                confidence=confidence,
                reasoning=reasoning,
                support_levels=[entry_support] if entry_support else [],
            )
        except Exception as e:
            logger.error(f"Error generating LeftSideLeaps for {symbol}: {e}")
            return None

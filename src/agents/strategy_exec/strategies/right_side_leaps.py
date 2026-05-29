"""右侧跟随 LEAPS Call 策略。"""

from __future__ import annotations

import logging
from typing import Any

from src.models import RecommendedOption, SupportResistanceLevel

from ..market_context import StrategyMarketContext
from .base import StrategyGenerator

logger = logging.getLogger(__name__)


class RightSideLeapsStrategy(StrategyGenerator):
    """右侧跟随 LEAPS Call 策略。

    确认上升趋势 + 动量加速 + 不超买时入场。
    入场条件需满足 ≥ 3/4。
    """

    name = "right_side_leaps"

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
            conditions_total = 4

            # 条件 1: SMA50 > SMA200（均线多头排列）— 从指标判断
            sma_bullish = False
            if market_context and hasattr(market_context, "sma_trend"):
                sma_bullish = market_context.sma_trend == "bullish"
            if sma_bullish:
                conditions_met += 1

            # 条件 2: RSI 45-65（动量健康）
            rsi_healthy = False
            if market_context and hasattr(market_context, "technical_rsi"):
                rsi = market_context.technical_rsi
                if 45 <= rsi <= 65:
                    rsi_healthy = True
                    conditions_met += 1

            # 条件 3: 成交量放大
            vol_expanding = False
            if market_context and hasattr(market_context, "relative_volume"):
                if market_context.relative_volume > 1.2:
                    vol_expanding = True
                    conditions_met += 1

            # 条件 4: 宏观 Regime 是 risk_on 或 neutral
            regime_ok = False
            if market_context and hasattr(market_context, "macro_regime"):
                if market_context.macro_regime in ("risk_on", "neutral"):
                    regime_ok = True
                    conditions_met += 1
            else:
                regime_ok = True
                conditions_met += 1

            if conditions_met < 3:
                logger.info(
                    f"RightSideLeaps for {symbol}: {conditions_met}/{conditions_total} conditions met, "
                    f"need >= 3, skipping"
                )
                return None

            leaps_calls = [
                c
                for c in options_chain.calls
                if c.is_leaps and c.delta and 0.65 <= c.delta <= 0.75
            ]
            if not leaps_calls:
                logger.warning(f"No suitable LEAPS Call options for {symbol}")
                return None

            leaps_calls.sort(key=lambda c: abs(c.delta - 0.7) if c.delta else float("inf"))
            best_call = leaps_calls[0]
            entry_price = best_call.mid_price or best_call.last_price or 0.0
            if entry_price <= 0:
                return None

            target_price = entry_price * 1.8 if entry_price > 0 else None
            stop_loss = entry_price * 0.6 if entry_price > 0 else None

            risk_reward_ratio = None
            if target_price and stop_loss:
                potential_gain = target_price - entry_price
                max_loss = entry_price - stop_loss
                if max_loss > 0:
                    risk_reward_ratio = potential_gain / max_loss

            confidence = 0.55
            if sma_bullish:
                confidence += 0.1
            if rsi_healthy:
                confidence += 0.05
            if vol_expanding:
                confidence += 0.05
            if regime_ok:
                confidence += 0.05
            confidence = max(0.1, min(1.0, confidence))

            reasoning = f"Right-Side LEAPS Call for {symbol}:\n"
            reasoning += f"  • Conditions met: {conditions_met}/{conditions_total}\n"
            reasoning += f"  • SMA bullish: {'Yes' if sma_bullish else 'No'}\n"
            reasoning += f"  • RSI healthy: {'Yes' if rsi_healthy else 'No'}\n"
            reasoning += f"  • Volume expanding: {'Yes' if vol_expanding else 'No'}\n"
            reasoning += "  • Entry: single tranche (100%)\n"
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
                support_levels=[],
            )
        except Exception as e:
            logger.error(f"Error generating RightSideLeaps for {symbol}: {e}")
            return None

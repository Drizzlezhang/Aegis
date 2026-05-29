"""决策质量评分 — 量化历史决策的好坏。"""

from dataclasses import dataclass


@dataclass
class DecisionScore:
    """决策质量评分结果。"""
    decision_id: str
    symbol: str
    total_score: float  # 0-100
    timing_score: float  # 0-30: 入场时机
    sizing_score: float  # 0-20: 仓位大小
    exit_score: float    # 0-30: 退出质量
    plan_adherence: float  # 0-20: 是否遵循 trade plan
    tags: list[str]  # 如 ["early_entry", "held_too_long", "perfect_exit"]


class DecisionScorer:
    """评估历史决策质量。

    评分维度:
    1. Timing (30pts): 入场价 vs 后续最低价的距离
       - 回撤 < 5% → 30
       - 回撤 5-15% → 20
       - 回撤 15-30% → 10
       - 回撤 > 30% → 0-5
    2. Sizing (20pts): 盈利时仓位是否足够大，亏损时是否过大
       - 盈利 + 仓位 >= 标准 → 20
       - 盈利 + 仓位偏小 → 12
       - 亏损 + 仓位过大 → 5
       - 亏损 + 仓位合理 → 15
    3. Exit (30pts): 是否在合理位置退出
       - 达到 target 退出 → 30
       - 合理止损 → 20
       - 提前退出（错过利润 > 20%）→ 10
       - 过度持有（从盈利变亏损）→ 5
    4. Plan Adherence (20pts): 实际行为 vs 原始 trade plan
       - 完全遵循 → 20
       - 小幅偏离 → 12
       - 严重偏离 → 5
    """

    def score(self, decision: dict, position_history: dict) -> DecisionScore:
        """评分一条已完成的决策。

        Args:
            decision: {"id", "symbol", "entry_price", "target_pct", "stop_loss_pct", "strategy_type"}
            position_history: {"prices_after_entry": list[float], "exit_price": float|None,
                             "exit_reason": str, "position_size_pct": float, "days_held": int}
        """
        timing = self._score_timing(decision, position_history)
        sizing = self._score_sizing(decision, position_history)
        exit_quality = self._score_exit(decision, position_history)
        adherence = self._score_plan_adherence(decision, position_history)
        tags = self._generate_tags(timing, sizing, exit_quality, adherence, position_history)

        return DecisionScore(
            decision_id=decision["id"],
            symbol=decision["symbol"],
            total_score=timing + sizing + exit_quality + adherence,
            timing_score=timing,
            sizing_score=sizing,
            exit_score=exit_quality,
            plan_adherence=adherence,
            tags=tags,
        )

    def _score_timing(self, decision: dict, history: dict) -> float:
        """入场时机评分 (0-30)。"""
        prices = history.get("prices_after_entry", [])
        if not prices:
            return 15.0  # 无数据给中间分
        entry_price = decision.get("entry_price", prices[0])
        min_price = min(prices[:30]) if len(prices) >= 30 else min(prices)
        max_drawdown_pct = (entry_price - min_price) / entry_price * 100 if entry_price > 0 else 0

        if max_drawdown_pct < 5:
            return 30.0
        elif max_drawdown_pct < 15:
            return 20.0
        elif max_drawdown_pct < 30:
            return 10.0
        else:
            return max(0.0, 5.0 - (max_drawdown_pct - 30) / 10)

    def _score_sizing(self, decision: dict, history: dict) -> float:
        """仓位大小评分 (0-20)。"""
        size_pct = history.get("position_size_pct", 5.0)
        exit_price = history.get("exit_price")
        entry_price = decision.get("entry_price", 0)

        if not exit_price or not entry_price:
            return 12.0

        pnl_pct = (exit_price - entry_price) / entry_price * 100
        is_profit = pnl_pct > 0
        standard_size = 5.0  # 标准仓位 5%

        if is_profit and size_pct >= standard_size:
            return 20.0
        elif is_profit and size_pct < standard_size:
            return 12.0
        elif not is_profit and size_pct > standard_size * 1.5:
            return 5.0
        else:
            return 15.0

    def _score_exit(self, decision: dict, history: dict) -> float:
        """退出质量评分 (0-30)。"""
        exit_reason = history.get("exit_reason", "unknown")
        exit_price = history.get("exit_price")
        entry_price = decision.get("entry_price", 0)
        decision.get("target_pct", 20.0)

        if not exit_price or not entry_price:
            return 15.0

        pnl_pct = (exit_price - entry_price) / entry_price * 100

        if exit_reason == "target_hit":
            return 30.0
        elif exit_reason == "stop_loss" and pnl_pct >= -decision.get("stop_loss_pct", 10) * 1.2:
            return 20.0  # 在止损附近执行
        elif exit_reason == "early_exit" and pnl_pct > 0:
            # 检查是否错过太多利润
            prices = history.get("prices_after_entry", [])
            if prices:
                max_price = max(prices)
                missed_pct = (max_price - exit_price) / entry_price * 100
                if missed_pct > 20:
                    return 10.0
            return 20.0
        elif pnl_pct < 0 and history.get("was_profitable", False):
            return 5.0  # 从盈利变亏损
        else:
            return 15.0

    def _score_plan_adherence(self, decision: dict, history: dict) -> float:
        """计划遵循评分 (0-20)。"""
        adherence = history.get("plan_adherence", "unknown")
        if adherence == "full":
            return 20.0
        elif adherence == "minor_deviation":
            return 12.0
        elif adherence == "major_deviation":
            return 5.0
        return 12.0  # unknown 给中间分

    def _generate_tags(self, timing: float, sizing: float, exit_q: float, adherence: float, history: dict) -> list[str]:
        """生成描述性标签。"""
        tags = []
        if timing >= 28:
            tags.append("perfect_timing")
        elif timing <= 10:
            tags.append("poor_timing")
        if exit_q >= 28:
            tags.append("perfect_exit")
        elif exit_q <= 10:
            tags.append("held_too_long")
        if sizing <= 8:
            tags.append("oversized_loss")
        if adherence <= 8:
            tags.append("plan_deviated")
        if history.get("days_held", 0) > 60:
            tags.append("long_hold")
        return tags

"""持仓自动化规则引擎。"""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class RuleAction(StrEnum):
    ALERT = "alert"
    AUTO_CLOSE = "auto_close"
    SUGGEST_ROLL = "suggest_roll"
    INCREASE_MONITOR = "increase_monitor"


@dataclass
class RuleResult:
    """规则执行结果。"""
    rule_name: str
    action: RuleAction
    reason: str
    urgency: int  # 1-5, 5=最紧急
    metadata: dict[str, Any] = field(default_factory=dict)


class PositionRulesEngine:
    """持仓管理规则引擎。

    预置规则:
    1. DTE < 21 + 无利润 → suggest_roll
    2. P&L > target_pct → alert
    3. P&L < -stop_loss_pct → alert
    4. 连续 5 天下跌 + DTE < 45 → increase_monitor
    5. IV rank > 80% + 持有 long call → alert
    """

    def __init__(self, config: dict[str, Any] | None = None):
        self._config = config or {}
        self._rules: list[Callable] = self._build_default_rules()

    def evaluate(self, position: dict, market_data: dict) -> list[RuleResult]:
        """评估所有规则。

        Args:
            position: {"symbol", "dte_remaining", "entry_price", "current_price",
                      "target_pct", "stop_loss_pct", "strategy_type", "position_type"}
            market_data: {"price_history_5d": list, "iv_rank": float, ...}

        Returns:
            按 urgency 降序排列的规则触发结果
        """
        results = []
        for rule in self._rules:
            result = rule(position, market_data)
            if result:
                results.append(result)
        return sorted(results, key=lambda r: r.urgency, reverse=True)

    def _build_default_rules(self) -> list[Callable]:
        """构建默认规则集。"""
        return [
            self._rule_dte_theta_decay,
            self._rule_profit_target,
            self._rule_stop_loss,
            self._rule_consecutive_decline,
            self._rule_high_iv_rank,
        ]

    def _rule_dte_theta_decay(self, position: dict, market_data: dict) -> RuleResult | None:
        """DTE < 21 + 未盈利 → 建议 Roll。"""
        dte = position.get("dte_remaining")
        if dte is None or dte >= 21:
            return None
        pnl_pct = self._calc_pnl_pct(position)
        if pnl_pct is not None and pnl_pct < 10.0:
            return RuleResult(
                rule_name="theta_decay_warning",
                action=RuleAction.SUGGEST_ROLL,
                reason=f"{position['symbol']}: DTE={dte}, P&L={pnl_pct:.1f}% — theta decay accelerating",
                urgency=4,
            )
        return None

    def _rule_profit_target(self, position: dict, market_data: dict) -> RuleResult | None:
        """达到止盈目标 → alert。"""
        pnl_pct = self._calc_pnl_pct(position)
        target = position.get("target_pct", 50.0)
        if pnl_pct is not None and pnl_pct >= target:
            return RuleResult(
                rule_name="profit_target_hit",
                action=RuleAction.ALERT,
                reason=f"{position['symbol']}: P&L={pnl_pct:.1f}% >= target {target}%",
                urgency=3,
                metadata={"pnl_pct": pnl_pct, "target_pct": target},
            )
        return None

    def _rule_stop_loss(self, position: dict, market_data: dict) -> RuleResult | None:
        """触及止损 → alert。"""
        pnl_pct = self._calc_pnl_pct(position)
        stop = position.get("stop_loss_pct", 20.0)
        if pnl_pct is not None and pnl_pct <= -stop:
            return RuleResult(
                rule_name="stop_loss_triggered",
                action=RuleAction.ALERT,
                reason=f"{position['symbol']}: P&L={pnl_pct:.1f}% <= stop -{stop}%",
                urgency=5,
                metadata={"pnl_pct": pnl_pct, "stop_loss_pct": stop},
            )
        return None

    def _rule_consecutive_decline(self, position: dict, market_data: dict) -> RuleResult | None:
        """连续 5 天下跌 + DTE < 45 → 加强监控。"""
        history = market_data.get("price_history_5d", [])
        if len(history) < 5:
            return None
        all_declining = all(history[i] > history[i+1] for i in range(len(history)-1))
        dte = position.get("dte_remaining", 999)
        if all_declining and dte < 45:
            return RuleResult(
                rule_name="consecutive_decline",
                action=RuleAction.INCREASE_MONITOR,
                reason=f"{position['symbol']}: 连续{len(history)}天下跌, DTE={dte}",
                urgency=3,
            )
        return None

    def _rule_high_iv_rank(self, position: dict, market_data: dict) -> RuleResult | None:
        """IV rank > 80% + 持有 long call → 考虑止盈。"""
        iv_rank = market_data.get("iv_rank")
        if iv_rank is None or iv_rank <= 80:
            return None
        pos_type = position.get("position_type", "")
        if "long" in pos_type.lower() and "call" in pos_type.lower():
            return RuleResult(
                rule_name="high_iv_long_call",
                action=RuleAction.ALERT,
                reason=f"{position['symbol']}: IV Rank={iv_rank}%, 持有 long call — 考虑止盈锁定 vega 利润",
                urgency=3,
            )
        return None

    @staticmethod
    def _calc_pnl_pct(position: dict) -> float | None:
        """计算持仓盈亏百分比。"""
        entry = position.get("entry_price")
        current = position.get("current_price")
        if entry and current and entry > 0:
            return (current - entry) / entry * 100
        return None

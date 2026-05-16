"""统计数据服务 — 为仪表盘提供聚合统计。"""

from dataclasses import dataclass


@dataclass
class TradingStats:
    """交易统计。"""
    total_decisions: int
    total_positions: int
    win_rate: float  # 0-1
    avg_pnl_pct: float
    total_realized_pnl: float
    best_trade: dict | None  # {"symbol", "pnl_pct", "date"}
    worst_trade: dict | None
    avg_holding_days: float
    monthly_pnl: dict[str, float]  # "2026-05": 1234.56
    by_strategy: dict[str, dict]  # strategy_type → {win_rate, avg_pnl, count}
    by_symbol: dict[str, dict]   # symbol → {win_rate, avg_pnl, count}


class StatsService:
    """统计数据聚合服务。只读，不修改任何数据。"""

    def __init__(self, decision_log, position_service):
        self._decisions = decision_log
        self._positions = position_service

    async def get_trading_stats(self, days: int = 90) -> TradingStats:
        """获取指定时间范围内的交易统计。"""
        decisions = await self._decisions.get_recent(days=days)
        positions = await self._positions.get_closed_positions(days=days)
        
        if not decisions and not positions:
            return TradingStats(
                total_decisions=0, total_positions=0, win_rate=0.0,
                avg_pnl_pct=0.0, total_realized_pnl=0.0,
                best_trade=None, worst_trade=None,
                avg_holding_days=0.0, monthly_pnl={},
                by_strategy={}, by_symbol={},
            )
        
        # 计算统计
        wins = [p for p in positions if p.get("pnl_pct", 0) > 0]
        win_rate = len(wins) / len(positions) if positions else 0.0
        avg_pnl = sum(p.get("pnl_pct", 0) for p in positions) / len(positions) if positions else 0.0
        total_pnl = sum(p.get("realized_pnl", 0) for p in positions)
        
        # Best/Worst
        sorted_by_pnl = sorted(positions, key=lambda p: p.get("pnl_pct", 0))
        best = {"symbol": sorted_by_pnl[-1]["symbol"], "pnl_pct": sorted_by_pnl[-1].get("pnl_pct", 0)} if sorted_by_pnl else None
        worst = {"symbol": sorted_by_pnl[0]["symbol"], "pnl_pct": sorted_by_pnl[0].get("pnl_pct", 0)} if sorted_by_pnl else None
        
        # Avg holding days
        avg_days = sum(p.get("days_held", 0) for p in positions) / len(positions) if positions else 0.0
        
        # Monthly PnL
        monthly = self._group_monthly_pnl(positions)
        
        # By strategy
        by_strategy = self._group_by_field(positions, "strategy_type")
        
        # By symbol
        by_symbol = self._group_by_field(positions, "symbol")
        
        return TradingStats(
            total_decisions=len(decisions),
            total_positions=len(positions),
            win_rate=win_rate,
            avg_pnl_pct=avg_pnl,
            total_realized_pnl=total_pnl,
            best_trade=best,
            worst_trade=worst,
            avg_holding_days=avg_days,
            monthly_pnl=monthly,
            by_strategy=by_strategy,
            by_symbol=by_symbol,
        )

    async def get_decision_quality_distribution(self) -> dict[str, int]:
        """获取决策质量评分分布。"""
        decisions = await self._decisions.get_scored()
        distribution = {"excellent": 0, "good": 0, "average": 0, "poor": 0}
        for d in decisions:
            score = d.get("quality_score", 0) or 0
            if score >= 80:
                distribution["excellent"] += 1
            elif score >= 60:
                distribution["good"] += 1
            elif score >= 40:
                distribution["average"] += 1
            else:
                distribution["poor"] += 1
        return distribution

    async def get_strategy_performance(self) -> list[dict]:
        """按策略类型分组的表现统计。"""
        positions = await self._positions.get_closed_positions(days=365)
        by_strategy = self._group_by_field(positions, "strategy_type")
        return [
            {"strategy_type": k, **v}
            for k, v in by_strategy.items()
        ]

    def _group_monthly_pnl(self, positions: list[dict]) -> dict[str, float]:
        """按月分组 PnL。"""
        monthly: dict[str, float] = {}
        for p in positions:
            month = p.get("close_date", "")[:7]  # "2026-05"
            if month:
                monthly[month] = monthly.get(month, 0.0) + p.get("realized_pnl", 0)
        return monthly

    def _group_by_field(self, positions: list[dict], field: str) -> dict[str, dict]:
        """按字段分组统计。"""
        groups: dict[str, list] = {}
        for p in positions:
            key = p.get(field, "unknown")
            groups.setdefault(key, []).append(p)
        
        result = {}
        for key, items in groups.items():
            wins = [i for i in items if i.get("pnl_pct", 0) > 0]
            result[key] = {
                "count": len(items),
                "win_rate": len(wins) / len(items) if items else 0.0,
                "avg_pnl": sum(i.get("pnl_pct", 0) for i in items) / len(items) if items else 0.0,
            }
        return result
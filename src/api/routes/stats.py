"""Stats API routes for dashboard and backtest result views."""

from fastapi import APIRouter

from src.agents.position_monitor.position_manager import PositionManager
from src.services import DecisionLog, PositionService, StatsService

router = APIRouter()


async def _build_stats_service() -> StatsService:
    manager = PositionManager()
    await manager.load()
    decision_log = DecisionLog()
    position_service = PositionService(manager)
    return StatsService(decision_log, position_service)


@router.get("/stats/trading")
async def get_trading_stats(days: int = 90) -> dict:
    """Return aggregate trading statistics for the last ``days`` days."""
    service = await _build_stats_service()
    stats = await service.get_trading_stats(days=days)
    return {
        "total_decisions": stats.total_decisions,
        "total_positions": stats.total_positions,
        "win_rate": stats.win_rate,
        "avg_pnl_pct": stats.avg_pnl_pct,
        "total_realized_pnl": stats.total_realized_pnl,
        "best_trade": stats.best_trade,
        "worst_trade": stats.worst_trade,
        "avg_holding_days": stats.avg_holding_days,
        "monthly_pnl": stats.monthly_pnl,
        "by_strategy": stats.by_strategy,
        "by_symbol": stats.by_symbol,
    }


@router.get("/stats/strategy-performance")
async def get_strategy_performance() -> list[dict]:
    """Return performance grouped by strategy type."""
    service = await _build_stats_service()
    return await service.get_strategy_performance()


@router.get("/stats/decision-quality")
async def get_decision_quality() -> dict[str, int]:
    """Return decision quality score distribution."""
    service = await _build_stats_service()
    return await service.get_decision_quality_distribution()

"""Stats API routes for dashboard and backtest result views."""

from fastapi import APIRouter, Request

from src.services import StatsService

router = APIRouter()


def _get_stats_service(request: Request) -> StatsService:
    service = getattr(request.app.state, "stats_service", None)
    if service is None:
        raise RuntimeError("StatsService is not initialized in app.state.stats_service")
    return service


@router.get("/stats/trading")
async def get_trading_stats(request: Request, days: int = 90) -> dict:
    """Return aggregate trading statistics for the last ``days`` days."""
    service = _get_stats_service(request)
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
async def get_strategy_performance(request: Request) -> list[dict]:
    """Return performance grouped by strategy type."""
    service = _get_stats_service(request)
    return await service.get_strategy_performance()


@router.get("/stats/decision-quality")
async def get_decision_quality(request: Request) -> dict[str, int]:
    """Return decision quality score distribution."""
    service = _get_stats_service(request)
    return await service.get_decision_quality_distribution()

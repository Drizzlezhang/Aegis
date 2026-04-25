"""Market data API routes."""

from typing import Any

from fastapi import APIRouter

from src.skills import get_global_registry

router = APIRouter(tags=["market"])


@router.get("/market/indices")
async def get_market_indices() -> dict[str, Any]:
    """Get market index snapshots (SPX, NDX, VIX, HSI, DJI)."""
    registry = get_global_registry()
    skill = registry.get_skill("yfinance_ohlcv")

    if not skill:
        return {"indices": [], "error": "yfinance skill not available"}

    try:
        result = await skill.execute({
            "symbol": "SPY",
            "data_type": "market_indices",
        })

        if result.success:
            return {"indices": result.data, "count": len(result.data)}
        return {"indices": [], "error": result.error}
    except Exception as e:
        return {"indices": [], "error": str(e)}

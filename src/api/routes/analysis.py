"""Analysis history API routes."""

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()


class HistoryEntry(BaseModel):
    """Analysis history entry."""
    id: int
    symbol: str
    tradeDate: str
    agentSequence: list[str]
    recommendationsCount: int
    executionTime: float
    success: bool


_HISTORY: list[HistoryEntry] = [
    HistoryEntry(id=1, symbol="QQQ", tradeDate="2026-04-24", agentSequence=["Data-Harvester", "Quant-Brain", "Strategy-Execution", "Aegis-Memory"], recommendationsCount=3, executionTime=12.5, success=True),
    HistoryEntry(id=2, symbol="SPY", tradeDate="2026-04-24", agentSequence=["Data-Harvester", "Quant-Brain", "Strategy-Execution", "Aegis-Memory"], recommendationsCount=2, executionTime=11.8, success=True),
    HistoryEntry(id=3, symbol="NVDA", tradeDate="2026-04-24", agentSequence=["Data-Harvester", "Quant-Brain", "Strategy-Execution", "Aegis-Memory"], recommendationsCount=3, executionTime=14.2, success=True),
    HistoryEntry(id=4, symbol="AAPL", tradeDate="2026-04-23", agentSequence=["Data-Harvester", "Quant-Brain", "Strategy-Execution", "Aegis-Memory"], recommendationsCount=0, executionTime=10.5, success=True),
    HistoryEntry(id=5, symbol="INTC", tradeDate="2026-04-23", agentSequence=["Data-Harvester"], recommendationsCount=0, executionTime=2.1, success=False),
    HistoryEntry(id=6, symbol="TSLA", tradeDate="2026-04-22", agentSequence=["Data-Harvester", "Quant-Brain", "Strategy-Execution", "Aegis-Memory"], recommendationsCount=2, executionTime=13.7, success=True),
    HistoryEntry(id=7, symbol="PLTR", tradeDate="2026-04-22", agentSequence=["Data-Harvester", "Quant-Brain", "Strategy-Execution", "Aegis-Memory"], recommendationsCount=3, executionTime=12.9, success=True),
    HistoryEntry(id=8, symbol="KO", tradeDate="2026-04-21", agentSequence=["Data-Harvester", "Quant-Brain", "Strategy-Execution", "Aegis-Memory"], recommendationsCount=1, executionTime=11.2, success=True),
]


@router.get("/analysis", response_model=list[HistoryEntry])
async def get_analysis_history(
    symbol: str | None = Query(None, description="Filter by symbol"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
) -> list[HistoryEntry]:
    """Get analysis history with optional filtering."""
    results = _HISTORY
    if symbol:
        results = [r for r in results if r.symbol == symbol.upper()]
    return results[:limit]

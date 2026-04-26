"""Analysis history API routes."""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.agents.aegis_memory.storage import AnalysisStorage
from src.config import get_config

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


class AnalysisDetail(BaseModel):
    """Full analysis detail."""
    id: int
    symbol: str
    tradeDate: str
    agentSequence: list[str]
    recommendations: list[dict[str, Any]]
    actionReport: str
    executionTime: float
    success: bool
    createdAt: str


def _get_storage() -> AnalysisStorage:
    """Get AnalysisStorage instance."""
    config = get_config()
    db_path = Path(config.memory.sqlite_path).expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    storage = AnalysisStorage(db_path)
    storage.ensure_schema()
    return storage


@router.get("/analysis", response_model=list[HistoryEntry])
async def get_analysis_history(
    symbol: str | None = Query(None, description="Filter by symbol"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
) -> list[HistoryEntry]:
    """Get analysis history with optional filtering."""
    storage = _get_storage()
    rows = storage.get_analysis_history(symbol=symbol, limit=limit)
    return [
        HistoryEntry(
            id=r["id"],
            symbol=r["symbol"],
            tradeDate=r["tradeDate"],
            agentSequence=r["agentSequence"],
            recommendationsCount=r["recommendationsCount"],
            executionTime=r["executionTime"],
            success=r["success"],
        )
        for r in rows
    ]


@router.get("/analysis/{analysis_id}", response_model=AnalysisDetail)
async def get_analysis_detail(analysis_id: int) -> AnalysisDetail:
    """Get full analysis detail by ID."""
    storage = _get_storage()
    row = storage.get_analysis_by_id(analysis_id)
    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return AnalysisDetail(
        id=row["id"],
        symbol=row["symbol"],
        tradeDate=row["tradeDate"],
        agentSequence=row["agentSequence"],
        recommendations=row["recommendations"],
        actionReport=row["actionReport"] or "",
        executionTime=row["executionTime"],
        success=row["success"],
        createdAt=row["createdAt"] or "",
    )

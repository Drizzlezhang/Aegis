"""Aegis-Memory API routes for semantic search and memory retrieval."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.agents.aegis_memory.agent import AegisMemoryAgent

router = APIRouter()

# Global aegis_memory instance (initialized via lifespan or on-demand)
_aegis_memory: AegisMemoryAgent | None = None


def set_aegis_memory(agent: AegisMemoryAgent) -> None:
    """Set the AegisMemoryAgent instance from lifespan."""
    global _aegis_memory
    _aegis_memory = agent


def _get_aegis_memory() -> AegisMemoryAgent:
    """Get or create AegisMemoryAgent instance."""
    global _aegis_memory
    if _aegis_memory is None:
        _aegis_memory = AegisMemoryAgent()
    return _aegis_memory


class SearchRequest(BaseModel):
    """Semantic search request."""
    query: str
    symbol: str | None = None
    limit: int = 5


class SearchResultItem(BaseModel):
    """Single search result."""
    id: int
    document: str
    metadata: dict[str, Any]
    similarity_score: float


class SearchResponse(BaseModel):
    """Search response."""
    results: list[SearchResultItem]
    query: str
    count: int


class MarketNoteItem(BaseModel):
    """Market note item."""
    id: int
    symbol: str | None
    note_date: str
    category: str
    content: str
    tags: list[str]
    created_at: str


class StatsResponse(BaseModel):
    """Vector store stats response."""
    analysis_results: int
    market_notes: int
    trading_actions: int
    total: int
    embedding_dimension: int
    storage_path: str


@router.post("/memory/search", response_model=SearchResponse)
async def search_memory(request: SearchRequest) -> SearchResponse:
    """Search analysis results by semantic similarity."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query is required")

    agent = _get_aegis_memory()
    try:
        raw_results = await agent.search_analysis_semantic(
            request.query,
            symbol=request.symbol,
            limit=request.limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}") from e

    results = []
    for r in raw_results:
        meta = r.get("vector_metadata", {})
        distance = meta.get("distance", 1.0)
        similarity = max(0.0, 1.0 - distance)
        results.append(
            SearchResultItem(
                id=r.get("id", 0),
                document=meta.get("document", ""),
                metadata={
                    "symbol": r.get("symbol", ""),
                    "trade_date": r.get("trade_date", ""),
                },
                similarity_score=round(similarity, 4),
            )
        )

    return SearchResponse(
        results=results,
        query=request.query,
        count=len(results),
    )


@router.get("/memory/notes", response_model=list[MarketNoteItem])
async def get_market_notes(
    symbol: str | None = Query(None, description="Filter by symbol"),
    category: str | None = Query(None, description="Filter by category"),
    limit: int = Query(20, ge=1, le=100),
) -> list[MarketNoteItem]:
    """Get market notes with optional filtering."""
    agent = _get_aegis_memory()
    try:
        rows = await agent.recall_market_notes(symbol=symbol, category=category, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch notes: {e}") from e

    return [
        MarketNoteItem(
            id=r["id"],
            symbol=r.get("symbol"),
            note_date=r["note_date"],
            category=r["category"],
            content=r["content"],
            tags=r.get("tags", []),
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.get("/memory/stats", response_model=StatsResponse)
async def get_memory_stats() -> StatsResponse:
    """Get vector store statistics."""
    agent = _get_aegis_memory()
    try:
        stats = await agent.get_vector_store_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {e}") from e

    return StatsResponse(
        analysis_results=stats.get("analysis_results", 0),
        market_notes=stats.get("market_notes", 0),
        trading_actions=stats.get("trading_actions", 0),
        total=stats.get("total", 0),
        embedding_dimension=stats.get("embedding_dimension", 384),
        storage_path=stats.get("storage_path", ""),
    )

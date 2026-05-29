"""Analysis execution API routes."""

import asyncio
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.agents.aegis_memory.storage import AnalysisStorage
from src.config import get_config

router = APIRouter()

# Global orchestrator instance (initialized in lifespan)
_orchestrator: Any = None


def set_orchestrator(orch: Any) -> None:
    """Set the orchestrator instance."""
    global _orchestrator
    _orchestrator = orch


def _get_storage() -> AnalysisStorage:
    """Get AnalysisStorage instance."""
    config = get_config()
    db_path = Path(config.memory.sqlite_path).expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    storage = AnalysisStorage(db_path)
    storage.ensure_schema()
    return storage


class AnalyzeRequest(BaseModel):
    """Request to run analysis."""
    symbols: list[str]


class RecommendationItem(BaseModel):
    """Structured strategy recommendation."""
    type: str
    contractSymbol: str
    strike: float
    expiry: str
    entryPrice: float
    targetPrice: float | None = None
    stopLoss: float | None = None
    riskRewardRatio: float | None = None
    confidence: float
    reasoning: str


class AnalyzeResult(BaseModel):
    """Single symbol analysis result."""
    symbol: str
    status: str
    agentSequence: list[str]
    recommendationsCount: int
    executionTime: float
    report: str
    recommendations: list[RecommendationItem]
    metadata: dict[str, Any] = {}
    request_id: str = ""


class AnalyzeResponse(BaseModel):
    """Analysis batch response."""
    results: list[AnalyzeResult]
    totalTime: float


@router.post("/analyze", response_model=AnalyzeResponse)
async def run_analysis(request: AnalyzeRequest) -> AnalyzeResponse:
    """Run multi-agent analysis for given symbols."""
    if not request.symbols:
        raise HTTPException(status_code=400, detail="No symbols provided")

    if _orchestrator is None:
        raise HTTPException(status_code=503, detail="Analysis engine not initialized")

    symbols = [s.upper().strip() for s in request.symbols]
    start_time = time.time()

    try:
        # Run analysis with a timeout to prevent hanging
        states = await asyncio.wait_for(
            _orchestrator.analyze_symbols(symbols),
            timeout=120.0
        )
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail="Analysis timed out after 120 seconds") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}") from e

    # Build response
    results: list[AnalyzeResult] = []
    for state in states:
        recommendations = []
        for rec in state.recommended_options:
            recommendations.append(
                RecommendationItem(
                    type=rec.recommendation_type,
                    contractSymbol=rec.contract.contract_symbol,
                    strike=rec.contract.strike,
                    expiry=str(rec.contract.expiry),
                    entryPrice=rec.entry_price,
                    targetPrice=rec.target_price,
                    stopLoss=rec.stop_loss,
                    riskRewardRatio=rec.risk_reward_ratio,
                    confidence=round(rec.confidence, 2),
                    reasoning=rec.reasoning,
                )
            )

        success = "Pipeline Error" not in state.action_report
        results.append(
            AnalyzeResult(
                symbol=state.symbol,
                status="success" if success else "error",
                agentSequence=state.agent_sequence,
                recommendationsCount=len(state.recommended_options),
                executionTime=0.0,  # Per-symbol timing not tracked individually
                report=state.action_report or "",
                recommendations=recommendations,
                metadata=getattr(state, "metadata", {}),
                request_id=getattr(state, "metadata", {}).get("trace_id", ""),
            )
        )

    return AnalyzeResponse(
        results=results,
        totalTime=round(time.time() - start_time, 2),
    )

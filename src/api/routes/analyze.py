"""Analysis execution API routes."""

import asyncio
import time
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# Global orchestrator instance (initialized in lifespan)
_orchestrator: Any = None


def set_orchestrator(orch: Any) -> None:
    """Set the orchestrator instance."""
    global _orchestrator
    _orchestrator = orch


class AnalyzeRequest(BaseModel):
    """Request to run analysis."""
    symbols: list[str]


class AnalyzeResult(BaseModel):
    """Single symbol analysis result."""
    symbol: str
    status: str
    agentSequence: list[str]
    recommendationsCount: int
    executionTime: float
    report: str


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
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Analysis timed out after 120 seconds")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    results: list[AnalyzeResult] = []
    for state in states:
        results.append(
            AnalyzeResult(
                symbol=state.symbol,
                status="success" if "Pipeline Error" not in state.action_report else "error",
                agentSequence=state.agent_sequence,
                recommendationsCount=len(state.recommended_options),
                executionTime=0.0,  # Per-symbol timing not tracked individually
                report=state.action_report or "",
            )
        )

    return AnalyzeResponse(
        results=results,
        totalTime=round(time.time() - start_time, 2),
    )

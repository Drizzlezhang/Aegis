"""Streaming analysis API routes."""

import asyncio
import json
import time
from typing import Any, AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .analyze import AnalyzeResult, RecommendationItem, _orchestrator

router = APIRouter()

# Global orchestrator instance (initialized in lifespan)
_orchestrator: Any = None


def set_orchestrator(orch: Any) -> None:
    """Set orchestrator instance."""
    global _orchestrator
    _orchestrator = orch


class AnalyzeStreamRequest(BaseModel):
    """Request to stream analysis progress."""

    symbols: list[str]


def _serialize_result(state: Any) -> dict[str, Any]:
    recommendations = [
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
        for rec in state.recommended_options
    ]
    success = "Pipeline Error" not in state.action_report
    return AnalyzeResult(
        symbol=state.symbol,
        status="success" if success else "error",
        agentSequence=state.agent_sequence,
        recommendationsCount=len(state.recommended_options),
        executionTime=0.0,
        report=state.action_report or "",
        recommendations=recommendations,
    ).model_dump()


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/analyze/stream")
async def run_analysis_stream(request: AnalyzeStreamRequest) -> StreamingResponse:
    """Stream multi-agent analysis progress for given symbols."""
    if not request.symbols:
        raise HTTPException(status_code=400, detail="No symbols provided")

    if _orchestrator is None:
        raise HTTPException(status_code=503, detail="Analysis engine not initialized")

    symbols = [symbol.upper().strip() for symbol in request.symbols]

    async def event_stream() -> AsyncIterator[str]:
        start_time = time.time()
        queue: asyncio.Queue[str | None] = asyncio.Queue()
        total_symbols = len(symbols)
        completed_symbols = 0

        async def emit_started(**payload: Any) -> None:
            step = payload["step"]
            state = payload["state"]
            progress = int(((completed_symbols + ((step.index - 1) / max(step.total, 1))) / total_symbols) * 100)
            await queue.put(_sse("progress", {
                "symbol": state.symbol,
                "stage": step.display_name,
                "step": step.index,
                "totalSteps": step.total,
                "progress": progress,
            }))

        async def emit_completed(**payload: Any) -> None:
            state = payload["state"]
            await queue.put(_sse("step", {
                "symbol": state.symbol,
                "agentSequence": state.agent_sequence,
                "currentStep": state.current_step,
                "totalSteps": state.total_steps,
            }))

        async def emit_pipeline_completed(**payload: Any) -> None:
            nonlocal completed_symbols
            state = payload["state"]
            completed_symbols += 1
            await queue.put(_sse("result", {
                "result": _serialize_result(state),
                "progress": int((completed_symbols / total_symbols) * 100),
            }))

        _orchestrator.add_listener("step_started", emit_started)
        _orchestrator.add_listener("step_completed", emit_completed)
        _orchestrator.add_listener("pipeline_completed", emit_pipeline_completed)

        async def producer() -> None:
            try:
                await queue.put(_sse("start", {"symbols": symbols, "progress": 0}))
                await asyncio.wait_for(_orchestrator.analyze_symbols(symbols), timeout=120.0)
                await queue.put(_sse("done", {"totalTime": round(time.time() - start_time, 2), "progress": 100}))
            except asyncio.TimeoutError:
                await queue.put(_sse("error", {"message": "Analysis timed out after 120 seconds"}))
            except Exception as exc:
                await queue.put(_sse("error", {"message": f"Analysis failed: {str(exc)}"}))
            finally:
                _orchestrator.remove_listener("step_started", emit_started)
                _orchestrator.remove_listener("step_completed", emit_completed)
                _orchestrator.remove_listener("pipeline_completed", emit_pipeline_completed)
                await queue.put(None)

        producer_task = asyncio.create_task(producer())
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item
        finally:
            await producer_task

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )

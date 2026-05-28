"""Scheduler API routes."""

import asyncio

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from src.scheduler.history import get_session, list_history

router = APIRouter()


@router.get("/scheduler/status")
async def get_scheduler_status(request: Request):
    scheduler = request.app.state.scheduler
    return scheduler.status


@router.post("/scheduler/trigger")
async def trigger_daily_analysis(request: Request):
    scheduler = request.app.state.scheduler
    if scheduler.is_running:
        raise HTTPException(status_code=409, detail="Analysis already running")
    asyncio.create_task(scheduler.run_daily_analysis())
    return {"status": "triggered"}


@router.get("/scheduler/history")
async def get_scheduler_history(
    job_id: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    session = get_session()
    try:
        items = list_history(session, job_id=job_id, limit=limit)
        return {"items": items, "total": len(items)}
    finally:
        session.close()


class SingleAnalysisRequest(BaseModel):
    symbol: str


@router.post("/scheduler/analyze")
async def trigger_single_analysis(request: Request, req: SingleAnalysisRequest):
    scheduler = request.app.state.scheduler
    result = await scheduler.run_single(req.symbol)
    return result

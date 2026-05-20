"""Scheduler API routes."""

import asyncio

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()


@router.get("/scheduler/status")
async def get_scheduler_status(request: Request):
    scheduler = request.app.state.scheduler
    return scheduler.status


@router.post("/scheduler/trigger")
async def trigger_daily_analysis(request: Request):
    scheduler = request.app.state.scheduler
    if scheduler._running:
        raise HTTPException(status_code=409, detail="Analysis already running")
    asyncio.create_task(scheduler.run_daily_analysis())
    return {"status": "triggered"}


class SingleAnalysisRequest(BaseModel):
    symbol: str


@router.post("/scheduler/analyze")
async def trigger_single_analysis(request: Request, req: SingleAnalysisRequest):
    scheduler = request.app.state.scheduler
    result = await scheduler.run_single(req.symbol)
    return result
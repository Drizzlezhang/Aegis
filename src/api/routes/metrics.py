"""Metrics API endpoint."""

from fastapi import APIRouter
from src.llm.gateway import get_gateway
from src.observability.metrics import get_pipeline_metrics

router = APIRouter()


@router.get("/metrics")
async def get_metrics() -> dict:
    """返回系统指标 — LLM + Pipeline。"""
    gateway = get_gateway()
    return {
        "llm": gateway._metrics.snapshot() if gateway else {},
        "pipeline": get_pipeline_metrics().snapshot(),
    }
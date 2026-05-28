"""Metrics API endpoint."""

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from src.llm.gateway import get_gateway
from src.observability.metrics import get_pipeline_metrics

router = APIRouter()


@router.get("/metrics")
async def get_metrics(request: Request) -> dict:
    """返回系统指标 — LLM + Pipeline（含 per-agent 指标）。"""
    gateway = get_gateway()
    orchestrator = getattr(request.app.state, "orchestrator", None)
    pipeline_data = orchestrator.metrics.to_dict() if orchestrator else get_pipeline_metrics().to_dict()
    return {
        "llm": gateway._metrics.snapshot() if gateway else {},
        "pipeline": pipeline_data,
    }


@router.get("/metrics/prometheus", response_class=PlainTextResponse)
async def get_prometheus_metrics() -> str:
    """返回 Prometheus 文本格式指标（供 Prometheus 抓取）。"""
    try:
        from src.services.metrics import get_metrics_text
        return get_metrics_text()
    except ImportError:
        return "# prometheus_client not installed\n"


@router.get("/metrics/health")
async def get_health_summary(request: Request) -> dict:
    """Simplified health check with agent status."""
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if orchestrator is None:
        return {"status": "unknown", "total_pipeline_runs": 0, "unhealthy_agents": []}

    metrics = orchestrator.metrics
    unhealthy_agents = [
        name for name, m in metrics.agent_metrics.items()
        if m.total_runs > 5 and m.success_rate < 0.5
    ]

    return {
        "status": "degraded" if unhealthy_agents else "healthy",
        "total_pipeline_runs": metrics.total_runs,
        "unhealthy_agents": unhealthy_agents,
    }

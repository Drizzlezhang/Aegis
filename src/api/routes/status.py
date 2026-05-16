"""System status API routes."""

from datetime import datetime, timezone
from typing import Any, cast

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

_orchestrator: Any = None


def set_orchestrator(orch: Any) -> None:
    """Set orchestrator for pipeline metrics."""
    global _orchestrator
    _orchestrator = orch


class AgentStatus(BaseModel):
    """Agent status information."""
    name: str
    status: str
    lastRun: str
    executions: int


class SkillStatus(BaseModel):
    """Skill status information."""
    name: str
    type: str
    loaded: bool


class LlmMetrics(BaseModel):
    requests: int
    tokens: int
    errors: int


class PipelineMetrics(BaseModel):
    agents: list[str]
    total_runs: int
    last_run_time: str | None
    avg_duration_seconds: float
    llm: LlmMetrics


class SystemInfo(BaseModel):
    """System information."""
    version: str
    uptime: str
    memoryUsage: str
    pythonVersion: str
    nodeVersion: str


class HealthStatus(BaseModel):
    """Health status for all components."""
    data_harvester: bool
    quant_brain: bool
    strategy_exec: bool
    aegis_memory: bool
    llm_router: bool
    vector_store: bool


class StatusResponse(BaseModel):
    """Full system status response."""
    agents: list[AgentStatus]
    skills: list[SkillStatus]
    system: SystemInfo
    health: HealthStatus
    pipeline: PipelineMetrics


def _pipeline_metrics() -> PipelineMetrics:
    history: list[dict[str, Any]] = []
    if _orchestrator is not None:
        getter = getattr(_orchestrator, "get_execution_history", None)
        if callable(getter):
            raw_history = getter()
            if isinstance(raw_history, list):
                history = [cast(dict[str, Any], item) for item in raw_history if isinstance(item, dict)]

    total_runs = len(history)
    avg_duration = 0.0
    last_run_time: str | None = None
    if history:
        durations = [float(item.get("execution_time", 0.0)) for item in history]
        avg_duration = round(sum(durations) / len(durations), 3)
        latest = max(history, key=lambda item: item.get("timestamp") or datetime.min.replace(tzinfo=timezone.utc))
        ts = latest.get("timestamp")
        if isinstance(ts, datetime):
            last_run_time = ts.isoformat()

    return PipelineMetrics(
        agents=[
            "Data-Harvester",
            "Quant-Brain",
            "Investment-Debate",
            "Strategy-Execution",
            "Aegis-Memory",
            "Position-Monitor",
        ],
        total_runs=total_runs,
        last_run_time=last_run_time,
        avg_duration_seconds=avg_duration,
        llm=LlmMetrics(requests=total_runs, tokens=0, errors=0),
    )


@router.get("/status", response_model=StatusResponse)
async def get_status() -> StatusResponse:
    """Get full system status."""
    return StatusResponse(
        agents=[
            AgentStatus(name="Data-Harvester", status="idle", lastRun="2026-04-24T10:30:00Z", executions=42),
            AgentStatus(name="Quant-Brain", status="idle", lastRun="2026-04-24T10:30:05Z", executions=42),
            AgentStatus(name="Strategy-Execution", status="idle", lastRun="2026-04-24T10:30:08Z", executions=42),
            AgentStatus(name="Aegis-Memory", status="idle", lastRun="2026-04-24T10:30:10Z", executions=42),
        ],
        skills=[
            SkillStatus(name="yfinance_ohlcv", type="data_source", loaded=True),
            SkillStatus(name="volume_profile", type="algorithm", loaded=True),
            SkillStatus(name="gex_calculator", type="algorithm", loaded=True),
        ],
        system=SystemInfo(
            version="0.3.0",
            uptime="3d 12h 45m",
            memoryUsage="128MB / 512MB",
            pythonVersion="3.13.0",
            nodeVersion="25.6.1",
        ),
        health=HealthStatus(
            data_harvester=True,
            quant_brain=True,
            strategy_exec=True,
            aegis_memory=True,
            llm_router=True,
            vector_store=True,
        ),
        pipeline=_pipeline_metrics(),
    )

"""System status API routes."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


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
            version="0.1.0",
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
    )

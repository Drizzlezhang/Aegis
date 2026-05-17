"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.agents.aegis_memory.agent import AegisMemoryAgent
from src.agents.data_harvester.realtime import RealtimeManager
from src.agents.orchestrator import Orchestrator
from src.config import get_config

from .routes import analysis, backtest, market, memory, positions, stats, status, symbols, ws
from .routes import analyze as analyze_routes
from .routes import analyze_stream as analyze_stream_routes


@asynccontextmanager
async def lifespan(app_: FastAPI):
    """Application lifespan handler."""
    global _orchestrator
    config = get_config()
    app_.state.realtime_manager = RealtimeManager(
        stale_threshold_seconds=config.realtime.stale_threshold_seconds
    )
    _orchestrator = Orchestrator()
    await _orchestrator.initialize()
    analyze_routes.set_orchestrator(_orchestrator)
    analyze_stream_routes.set_orchestrator(_orchestrator)
    status.set_orchestrator(_orchestrator)
    aegis_memory = _orchestrator.get_agent("Aegis-Memory")
    if aegis_memory is not None:
        memory.set_aegis_memory(cast(AegisMemoryAgent, aegis_memory))
    yield
    _orchestrator = None

# Global orchestrator instance
_orchestrator: Orchestrator | None = None


app = FastAPI(
    title="Aegis-Trader API",
    description="Multi-Agent quantitative trading system API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(symbols.router, prefix="/api")
app.include_router(status.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(analyze_routes.router, prefix="/api")
app.include_router(analyze_stream_routes.router, prefix="/api")
app.include_router(market.router, prefix="/api")
app.include_router(backtest.router, prefix="/api")
app.include_router(memory.router, prefix="/api")
app.include_router(positions.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(ws.router)


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}

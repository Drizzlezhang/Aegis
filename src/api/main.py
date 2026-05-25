"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.agents.aegis_memory.agent import AegisMemoryAgent
from src.agents.data_harvester.realtime import RealtimeManager
from src.agents.orchestrator import Orchestrator
from src.agents.position_monitor.position_manager import PositionManager
from src.config import get_config
from src.observability.logging import setup_logging
from src.services import DecisionLog, PositionService, StatsService
from src.services.settings import SettingsService

from .middleware.auth import AuthMiddleware
from .middleware.rate_limit import RateLimitMiddleware
from src.scheduler.engine import AnalysisScheduler

from .routes import analysis, backtest, market, memory, metrics, positions, settings, stats, status, symbols, ws
from .routes import analyze as analyze_routes
from .routes import analyze_stream as analyze_stream_routes
from .routes import auth
from .routes import scheduler as scheduler_routes
from .routes import watchlist as watchlist_routes


@asynccontextmanager
async def lifespan(app_: FastAPI):
    """Application lifespan handler."""
    global _orchestrator
    config = get_config()

    log_json = config.profile.upper() == "PRODUCTION" if hasattr(config, 'profile') else False
    setup_logging(level="INFO", json_output=log_json)

    app_.state.realtime_manager = RealtimeManager(
        stale_threshold_seconds=config.realtime.stale_threshold_seconds
    )
    position_manager = PositionManager()
    await position_manager.load()
    app_.state.stats_service = StatsService(
        DecisionLog(),
        PositionService(position_manager),
    )
    app_.state.settings_service = SettingsService()
    _orchestrator = Orchestrator()
    await _orchestrator.initialize()
    analyze_routes.set_orchestrator(_orchestrator)
    analyze_stream_routes.set_orchestrator(_orchestrator)
    status.set_orchestrator(_orchestrator)
    aegis_memory = _orchestrator.get_agent("Aegis-Memory")
    if aegis_memory is not None:
        memory.set_aegis_memory(cast(AegisMemoryAgent, aegis_memory))

    # Scheduler
    app_.state.scheduler = AnalysisScheduler(_orchestrator)
    await app_.state.scheduler.initialize()
    app_.state.scheduler.start()

    yield
    # Scheduler cleanup
    app_.state.scheduler.stop()
    await app_.state.scheduler.aclose()

    if hasattr(app_.state, "realtime_manager"):
        app_.state.realtime_manager.shutdown()
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

# Security middleware — rate limit before auth
app.add_middleware(RateLimitMiddleware, rate=120, per=60)
app.add_middleware(AuthMiddleware)

# Include routers
app.include_router(auth.router, prefix="/api")
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
app.include_router(metrics.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(ws.router)
app.include_router(watchlist_routes.router, prefix="/api")
app.include_router(scheduler_routes.router, prefix="/api")


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}

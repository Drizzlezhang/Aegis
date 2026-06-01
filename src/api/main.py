"""FastAPI application entry point."""

import asyncio
import logging
import signal
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
from src.scheduler.engine import AnalysisScheduler
from src.services import DecisionLog, PositionService, StatsService
from src.services.event_bus import get_event_bus
from src.services.settings import SettingsService
from src.services.tracking.service import TrackingService

from .middleware.rate_limit import RateLimitMiddleware
from .routes import (
    analysis,
    backtest,
    data_routes,
    decisions,
    llm,
    market,
    memory,
    metrics,
    notifications,
    positions,
    settings,
    signals,
    stats,
    status,
    symbols,
    ws,
    ws_alerts,
    ws_llm,
    ws_phase,
)
from .routes import analyze as analyze_routes
from .routes import analyze_stream as analyze_stream_routes
from .routes import push_ws as push_ws_routes
from .routes import scheduler as scheduler_routes
from .routes import tracking as tracking_routes
from .routes import watchlist as watchlist_routes

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app_: FastAPI):
    """Application lifespan handler with graceful shutdown."""
    global _orchestrator
    config = get_config()

    # Log config validation warnings
    for warning in config.validation_warnings:
        logger.warning(f"Config validation: {warning}")

    if not config.is_production_ready:
        if config.strict_validation:
            logger.error("Config validation failed in strict mode. Exiting.")
            raise SystemExit("Config validation failed in strict mode. See warnings above.")
        logger.warning("Running with incomplete configuration. Some features may not work.")

    log_json = config.profile.upper() == "PRODUCTION" if hasattr(config, 'profile') else False
    setup_logging(level="INFO", json_output=log_json)

    # Start EventBus dispatch loop
    bus = get_event_bus()
    await bus.start()
    logger.info("EventBus dispatch loop started")

    # Push dispatcher — subscribe to PushEvent
    from src.config import get_config as _get_config
    from src.services.push_adapters.telegram_stub import TelegramStubAdapter
    from src.services.push_adapters.websocket import WebSocketAdapter
    from src.services.push_dispatcher import PushDispatcher

    _cfg = _get_config()
    ws_adapter = WebSocketAdapter()
    push_ws_routes.set_ws_adapter(ws_adapter)
    dispatcher = PushDispatcher(
        adapters={"telegram": TelegramStubAdapter(), "websocket": ws_adapter},
        db_path=_cfg.memory.sqlite_path,
    )
    bus.subscribe("PushEvent", dispatcher.dispatch)
    logger.info("PushDispatcher registered on EventBus")

    logger.info("Aegis API running in private deployment mode (no auth)")

    app_.state.realtime_manager = RealtimeManager(
        stale_threshold_seconds=config.realtime.stale_threshold_seconds
    )
    position_manager = PositionManager()
    await position_manager.load()
    app_.state.position_manager = position_manager
    app_.state.stats_service = StatsService(
        DecisionLog(),
        PositionService(position_manager),
    )
    app_.state.settings_service = SettingsService()

    # Notification router
    from src.services.notification.base import NotificationLevel
    from src.services.notification.router import NotificationRouter, RoutingRule
    from src.services.notification.telegram import TelegramNotifier

    notification_router = NotificationRouter()
    telegram = TelegramNotifier()
    notification_router.register_channel(telegram)
    notification_router.add_rule(RoutingRule("telegram", NotificationLevel.CRITICAL))
    notification_router.add_rule(RoutingRule("telegram", NotificationLevel.ERROR))
    app_.state.notification_router = notification_router

    _orchestrator = Orchestrator()
    await _orchestrator.initialize()
    analyze_routes.set_orchestrator(_orchestrator)
    analyze_stream_routes.set_orchestrator(_orchestrator)
    status.set_orchestrator(_orchestrator)
    ws.set_orchestrator(_orchestrator)
    aegis_memory = _orchestrator.get_agent("Aegis-Memory")
    if aegis_memory is not None:
        memory.set_aegis_memory(cast(AegisMemoryAgent, aegis_memory))

    # Scheduler
    app_.state.scheduler = AnalysisScheduler(_orchestrator)
    await app_.state.scheduler.initialize()
    app_.state.scheduler.start()

    # Tracking service
    app_.state.tracking_service = TrackingService()

    # Register signal handlers for graceful shutdown
    shutdown_event = asyncio.Event()

    def _signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, initiating graceful shutdown...")
        shutdown_event.set()

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    yield

    # === SHUTDOWN ===
    logger.info("Shutting down gracefully...")

    async def _do_shutdown():
        # 1. Stop scheduler (no new jobs)
        if hasattr(app_.state, "scheduler"):
            logger.info("Stopping scheduler...")
            try:
                app_.state.scheduler.stop()
                await app_.state.scheduler.aclose()
            except Exception as e:
                logger.warning(f"Error stopping scheduler: {e}")

        # 2. Close WebSocket connections
        if hasattr(app_.state, "ws_connections"):
            ws_conns = getattr(app_.state, "ws_connections", set())
            if ws_conns:
                logger.info(f"Closing {len(ws_conns)} WebSocket connections...")
                for ws in list(ws_conns):
                    try:
                        await ws.close(code=1001, reason="Server shutting down")
                    except Exception:
                        pass

        # 3. Save position state
        if hasattr(app_.state, "position_manager"):
            logger.info("Persisting position state...")
            try:
                await app_.state.position_manager.save()
            except Exception as e:
                logger.warning(f"Error saving positions: {e}")

        # 4. Shutdown realtime manager
        if hasattr(app_.state, "realtime_manager"):
            app_.state.realtime_manager.shutdown()

        # 5. Close notification channels
        if hasattr(app_.state, "notification_router"):
            try:
                await app_.state.notification_router.close()
            except Exception as e:
                logger.warning(f"Error closing notification router: {e}")

        # 6. Stop EventBus dispatch loop
        try:
            await get_event_bus().stop()
            logger.info("EventBus dispatch loop stopped")
        except Exception as e:
            logger.warning(f"Error stopping EventBus: {e}")

        _orchestrator = None

    try:
        await asyncio.wait_for(_do_shutdown(), timeout=30)
    except TimeoutError:
        logger.error("Shutdown timed out after 30s, forcing exit.")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

    logger.info("Shutdown complete.")

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

# Security middleware — rate limit
app.add_middleware(RateLimitMiddleware, rate=120, per=60)

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
app.include_router(metrics.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(ws.router)
app.include_router(ws_phase.router)
app.include_router(ws_alerts.router)
app.include_router(ws_llm.router)
app.include_router(push_ws_routes.router)
app.include_router(watchlist_routes.router, prefix="/api")
app.include_router(scheduler_routes.router, prefix="/api")
app.include_router(tracking_routes.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(signals.router, prefix="/api/signals")
app.include_router(decisions.router, prefix="/api/decisions")
app.include_router(data_routes.router)
app.include_router(llm.router)


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}

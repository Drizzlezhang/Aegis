"""WebSocket realtime price endpoints."""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.agents.data_harvester.realtime import PriceUpdate, RealtimeManager

logger = logging.getLogger(__name__)

router = APIRouter()

# Global orchestrator reference (set in lifespan)
_orchestrator: Any = None


def set_orchestrator(orch: Any) -> None:
    """Set orchestrator instance for WS analysis endpoint."""
    global _orchestrator
    _orchestrator = orch


def _serialize_update(kind: str, update: PriceUpdate) -> dict:
    return {
        "type": kind,
        "symbol": update.symbol.upper(),
        "price": update.price,
        "change": update.change,
        "change_pct": update.change_pct,
        "volume": update.volume,
        "timestamp": update.timestamp,
    }


@router.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket, symbols: str | None = None) -> None:
    """Stream realtime price snapshots and updates.

    Query params:
        symbols: optional comma-separated list, e.g. ``NVDA,TSLA``.
    """
    await websocket.accept()

    manager: RealtimeManager = websocket.app.state.realtime_manager
    queue = manager.subscribe()
    symbol_set = {s.strip().upper() for s in symbols.split(",") if s.strip()} if symbols else None

    try:
        for symbol, update in manager.get_all_latest().items():
            if symbol_set and symbol.upper() not in symbol_set:
                continue
            await websocket.send_json(_serialize_update("snapshot", update))

        while True:
            update = await queue.get()
            if symbol_set and update.symbol.upper() not in symbol_set:
                continue
            await websocket.send_json(_serialize_update("update", update))
    except WebSocketDisconnect:
        pass
    finally:
        manager.unsubscribe(queue)


@router.websocket("/ws/analysis/{request_id}")
async def analysis_progress_ws(websocket: WebSocket, request_id: str) -> None:
    """Stream pipeline progress events for a specific analysis request."""
    await websocket.accept()

    if _orchestrator is None:
        await websocket.close(code=1011, reason="Orchestrator not available")
        return

    queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=100)

    async def on_progress(**payload: Any) -> None:
        if payload.get("request_id") == request_id:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                logger.warning(
                    f"Analysis WS queue full for request_id={request_id}, dropping event"
                )

    _orchestrator.add_listener("pipeline_progress", on_progress)

    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        _orchestrator.remove_listener("pipeline_progress", on_progress)

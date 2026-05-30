"""WebSocket endpoint for real-time phase events."""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.services.event_bus import PhaseEvent, get_event_bus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/phase")
async def phase_stream(websocket: WebSocket, symbol: str | None = None) -> None:
    """Stream PhaseEvent updates, optionally filtered by symbol.

    Query params:
        symbol: optional single symbol filter, e.g. ``?symbol=AAPL``.
    """
    await websocket.accept()
    logger.info("Phase WS client connected (symbol=%s)", symbol)

    bus = get_event_bus()
    queue: asyncio.Queue[dict] = asyncio.Queue()

    async def on_phase(event: PhaseEvent) -> None:
        if symbol and event.symbol.upper() != symbol.upper():
            return
        await queue.put({
            "type": "phase",
            "symbol": event.symbol,
            "phase": event.phase,
            "confidence": event.confidence,
            "composite_score": event.composite_score,
            "transition": event.transition,
            "timestamp": event.timestamp.isoformat(),
        })

    handle = bus.subscribe("PhaseEvent", on_phase)

    try:
        while True:
            data = await queue.get()
            await websocket.send_json(data)
    except WebSocketDisconnect:
        pass
    finally:
        bus.unsubscribe(handle)
        logger.info("Phase WS client disconnected (symbol=%s)", symbol)

"""WebSocket endpoint for real-time alert events."""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.services.event_bus import AlertEvent, get_event_bus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/alerts")
async def alerts_stream(websocket: WebSocket) -> None:
    """Stream AlertEvent updates in real time."""
    await websocket.accept()
    logger.info("Alerts WS client connected")

    bus = get_event_bus()
    queue: asyncio.Queue[dict] = asyncio.Queue()

    async def on_alert(event: AlertEvent) -> None:
        await queue.put({
            "type": "alert",
            "rule_name": event.rule_name,
            "message": event.message,
            "severity": event.severity.value,
            "timestamp": event.timestamp.isoformat(),
        })

    handle = bus.subscribe("AlertEvent", on_alert)

    try:
        while True:
            data = await queue.get()
            await websocket.send_json(data)
    except WebSocketDisconnect:
        pass
    finally:
        bus.unsubscribe(handle)
        logger.info("Alerts WS client disconnected")

"""WebSocket route for push event streaming."""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.services.push_adapters.websocket import WebSocketAdapter

logger = logging.getLogger(__name__)

router = APIRouter()

# Module-level singleton — set by main.py lifespan
_ws_adapter: WebSocketAdapter | None = None


def set_ws_adapter(adapter: WebSocketAdapter) -> None:
    global _ws_adapter
    _ws_adapter = adapter


@router.websocket("/api/push/stream")
async def push_stream(ws: WebSocket) -> None:
    await ws.accept()
    if _ws_adapter is None:
        await ws.close(code=1011, reason="Push service not available")
        return

    await _ws_adapter.register(ws)
    try:
        while True:
            # keep connection alive; client may send pings
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket push stream error")
    finally:
        await _ws_adapter.unregister(ws)

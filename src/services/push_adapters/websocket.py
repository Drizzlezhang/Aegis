"""WebSocket push adapter — manages connected clients and broadcasts PushEvents."""

from __future__ import annotations

import logging

from fastapi import WebSocket

from src.services.event_bus import PushEvent
from src.services.push_adapters.base import PushAdapter

logger = logging.getLogger(__name__)


class WebSocketAdapter(PushAdapter):
    """Manages a set of WebSocket clients and broadcasts push events to all of them."""

    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()

    async def register(self, ws: WebSocket) -> None:
        """Register a new WebSocket client."""
        self._clients.add(ws)
        logger.info("WebSocket client connected (total: %d)", len(self._clients))

    async def unregister(self, ws: WebSocket) -> None:
        """Remove a disconnected WebSocket client."""
        self._clients.discard(ws)
        logger.info("WebSocket client disconnected (total: %d)", len(self._clients))

    async def send(self, event: PushEvent) -> bool:
        payload = {
            "event_id": event.event_id,
            "push_type": event.push_type,
            "title": event.title,
            "body": event.body_markdown,
            "symbols": event.related_symbols,
            "ts": event.timestamp.isoformat(),
        }
        # snapshot to avoid concurrent modification during iteration
        for ws in list(self._clients):
            try:
                await ws.send_json(payload)
            except Exception:
                logger.warning("WebSocket client send failed, removing")
                self._clients.discard(ws)
        return True

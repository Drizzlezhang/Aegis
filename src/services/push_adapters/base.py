"""Push adapter abstract base class and implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.services.event_bus import PushEvent


class PushAdapter(ABC):
    """Abstract base for push notification channels (Telegram, WebSocket, etc.)."""

    @abstractmethod
    async def send(self, event: PushEvent) -> bool:
        """Send a push event. Returns True on success."""
        ...

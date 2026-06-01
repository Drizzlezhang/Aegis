"""Telegram stub adapter — logs push events, real Telegram integration deferred to Branch F."""

from __future__ import annotations

import logging

from src.services.event_bus import PushEvent
from src.services.push_adapters.base import PushAdapter

logger = logging.getLogger(__name__)


class TelegramStubAdapter(PushAdapter):
    """Stub adapter that logs push events instead of sending to Telegram."""

    async def send(self, event: PushEvent) -> bool:
        body_preview = event.body_markdown[:120] if event.body_markdown else ""
        logger.info("[TG STUB] %s | %s", event.title, body_preview)
        return True

"""Real Telegram push adapter via Bot API."""

from __future__ import annotations

import logging

import httpx

from src.services.event_bus import PushEvent
from src.services.push_adapters.base import PushAdapter

logger = logging.getLogger(__name__)


class TelegramAdapter(PushAdapter):
    """Send push events to a Telegram chat via Bot API."""

    def __init__(self, bot_token: str, chat_id: str) -> None:
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    async def send(self, event: PushEvent) -> bool:
        text = f"*{event.title}*\n\n{event.body_markdown}"
        if event.related_symbols:
            text += f"\n\nSymbols: {', '.join(event.related_symbols)}"

        payload = {
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(self._url, json=payload)
                if resp.status_code != 200:
                    logger.error(
                        "Telegram API error: %s %s", resp.status_code, resp.text
                    )
                    return False
                logger.info(
                    "TelegramAdapter: sent event_id=%s to chat %s",
                    event.event_id,
                    self._chat_id,
                )
                return True
        except Exception:
            logger.exception(
                "TelegramAdapter.send failed for event_id=%s", event.event_id
            )
            return False

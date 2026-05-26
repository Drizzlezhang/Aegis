"""Webhook notification channel."""

import json
import logging
from string import Template

import httpx

from .base import Notification, NotificationChannel

logger = logging.getLogger(__name__)


class WebhookNotifier(NotificationChannel):
    """Send notifications via HTTP webhook (POST)."""

    def __init__(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        payload_template: str | None = None,
        timeout: float = 10.0,
        max_retries: int = 2,
    ):
        self._url = url
        self._headers = headers or {"Content-Type": "application/json"}
        self._template = payload_template
        self._timeout = timeout
        self._max_retries = max_retries
        self._client = httpx.AsyncClient(timeout=timeout)

    @property
    def channel_type(self) -> str:
        return "webhook"

    async def send(self, notification: Notification) -> bool:
        """POST notification to webhook URL."""
        payload = self._build_payload(notification)
        for attempt in range(self._max_retries + 1):
            try:
                resp = await self._client.post(
                    self._url, json=payload, headers=self._headers,
                )
                if resp.status_code < 400:
                    return True
            except httpx.HTTPError:
                if attempt == self._max_retries:
                    logger.warning(f"Webhook send failed after {self._max_retries + 1} attempts")
                    return False
        return False

    async def is_available(self) -> bool:
        """Check webhook URL is reachable."""
        try:
            resp = await self._client.head(self._url, timeout=5.0)
            return resp.status_code < 500
        except httpx.HTTPError:
            return False

    async def close(self) -> None:
        await self._client.aclose()

    def _build_payload(self, notification: Notification) -> dict:
        """Build webhook payload from notification."""
        if self._template:
            tpl = Template(self._template)
            body = tpl.safe_substitute(
                level=notification.level.value,
                title=notification.title,
                message=notification.message,
                category=notification.category.value,
            )
            return json.loads(body)

        return {
            "level": notification.level.value,
            "category": notification.category.value,
            "title": notification.title,
            "message": notification.message,
            "timestamp": notification.created_at.isoformat(),
            "metadata": notification.metadata,
        }

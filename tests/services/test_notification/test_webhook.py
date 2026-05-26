"""Tests for WebhookNotifier."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.notification.base import Notification, NotificationLevel, NotificationCategory
from src.services.notification.webhook import WebhookNotifier


def _make_notification(**kwargs) -> Notification:
    from datetime import datetime, timezone
    defaults = {
        "id": "test-001",
        "level": NotificationLevel.WARNING,
        "category": NotificationCategory.SYSTEM,
        "title": "Test",
        "message": "Test message",
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(kwargs)
    return Notification(**defaults)


class TestWebhookNotifier:
    def test_channel_type_is_webhook(self):
        notifier = WebhookNotifier("https://example.com/hook")
        assert notifier.channel_type == "webhook"

    @pytest.mark.asyncio
    async def test_send_success_on_200(self):
        notifier = WebhookNotifier("https://example.com/hook")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        notifier._client.post = AsyncMock(return_value=mock_resp)

        result = await notifier.send(_make_notification())
        assert result is True
        notifier._client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_retries_on_failure(self):
        notifier = WebhookNotifier("https://example.com/hook", max_retries=2)
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        notifier._client.post = AsyncMock(return_value=mock_resp)

        result = await notifier.send(_make_notification())
        assert result is False
        assert notifier._client.post.call_count == 3  # 1 initial + 2 retries

    @pytest.mark.asyncio
    async def test_is_available_checks_head(self):
        notifier = WebhookNotifier("https://example.com/hook")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        notifier._client.head = AsyncMock(return_value=mock_resp)

        assert await notifier.is_available() is True

        mock_resp.status_code = 503
        assert await notifier.is_available() is False

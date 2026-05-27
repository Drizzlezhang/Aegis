"""Tests for NotificationRouter."""

import pytest

from src.services.notification.base import (
    Notification,
    NotificationCategory,
    NotificationChannel,
    NotificationLevel,
)
from src.services.notification.router import NotificationRouter, RoutingRule


class FakeChannel(NotificationChannel):
    """Fake channel for testing."""

    def __init__(self, channel_type: str, available: bool = True, send_result: bool = True):
        self._type = channel_type
        self._available = available
        self._send_result = send_result
        self.sent: list[Notification] = []

    @property
    def channel_type(self) -> str:
        return self._type

    async def send(self, notification: Notification) -> bool:
        self.sent.append(notification)
        return self._send_result

    async def is_available(self) -> bool:
        return self._available

    async def close(self) -> None:
        pass


class TestNotificationRouter:
    def test_register_channel(self):
        router = NotificationRouter()
        ch = FakeChannel("telegram")
        router.register_channel(ch)
        assert router._channels["telegram"] is ch

    def test_add_rule_and_resolve(self):
        router = NotificationRouter()
        router.add_rule(RoutingRule("telegram", NotificationLevel.WARNING))
        router.add_rule(RoutingRule("webhook", NotificationLevel.CRITICAL))

        # INFO < WARNING → only no match
        targets = router._resolve_channels(NotificationLevel.INFO, NotificationCategory.SYSTEM)
        assert targets == set()

        # WARNING >= WARNING → telegram
        targets = router._resolve_channels(NotificationLevel.WARNING, NotificationCategory.SYSTEM)
        assert targets == {"telegram"}

        # CRITICAL >= WARNING and CRITICAL >= CRITICAL → both
        targets = router._resolve_channels(NotificationLevel.CRITICAL, NotificationCategory.SYSTEM)
        assert targets == {"telegram", "webhook"}

    @pytest.mark.asyncio
    async def test_dispatch_routes_to_channels(self):
        router = NotificationRouter()
        ch = FakeChannel("telegram")
        router.register_channel(ch)
        router.add_rule(RoutingRule("telegram", NotificationLevel.WARNING))

        succeeded = await router.dispatch(
            NotificationLevel.ERROR,
            NotificationCategory.ANALYSIS,
            "Error title",
            "Error message",
        )
        assert succeeded == ["telegram"]
        assert len(ch.sent) == 1
        assert ch.sent[0].title == "Error title"
        assert ch.sent[0].level == NotificationLevel.ERROR

    def test_get_history_with_limit(self):
        router = NotificationRouter()
        ch = FakeChannel("telegram")
        router.register_channel(ch)
        router.add_rule(RoutingRule("telegram", NotificationLevel.INFO))

        import asyncio

        async def _dispatch():
            for i in range(5):
                await router.dispatch(
                    NotificationLevel.INFO,
                    NotificationCategory.SYSTEM,
                    f"Title {i}",
                    f"Message {i}",
                )

        asyncio.run(_dispatch())

        history = router.get_history(limit=3)
        assert len(history) == 3
        # Most recent first
        assert history[0].title == "Title 4"

    def test_mark_read_and_unread_count(self):
        router = NotificationRouter()
        ch = FakeChannel("telegram")
        router.register_channel(ch)
        router.add_rule(RoutingRule("telegram", NotificationLevel.INFO))

        import asyncio

        async def _dispatch():
            await router.dispatch(
                NotificationLevel.INFO,
                NotificationCategory.SYSTEM,
                "Test",
                "Message",
            )

        asyncio.run(_dispatch())

        assert router.unread_count == 1

        history = router.get_history()
        nid = history[0].id
        assert router.mark_read(nid) is True
        assert router.unread_count == 0
        assert router.mark_read("nonexistent") is False

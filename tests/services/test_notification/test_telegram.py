"""Tests for TelegramNotifier."""

import pytest

from src.services.notification.telegram import TelegramNotifier


class TestTelegramNotifier:
    def test_disabled_returns_false(self, monkeypatch):
        """When telegram.enabled=False, send() returns False."""
        from src.config import get_config

        config = get_config()
        monkeypatch.setattr(config.telegram, "enabled", False)
        monkeypatch.setattr(config.telegram, "bot_token", "fake")
        monkeypatch.setattr(config.telegram, "chat_id", "123")

        notifier = TelegramNotifier()
        assert notifier.enabled is False

        import asyncio
        result = asyncio.run(notifier.send("test"))
        assert result is False

    def test_silent_hours_blocks_send(self, monkeypatch):
        """During silent hours, send() returns False unless force=True."""
        from datetime import datetime
        from src.config import get_config

        config = get_config()
        monkeypatch.setattr(config.telegram, "enabled", True)
        monkeypatch.setattr(config.telegram, "bot_token", "fake_token")
        monkeypatch.setattr(config.telegram, "chat_id", "123")
        monkeypatch.setattr(config.telegram, "silent_hours", (0, 23))
        monkeypatch.setattr(
            config.telegram, "notify_on_completion", True
        )
        monkeypatch.setattr(
            config.telegram, "notify_on_error", True
        )

        notifier = TelegramNotifier()

        # Mock _in_silent_hours to always return True
        monkeypatch.setattr(notifier, "_in_silent_hours", lambda: True)

        import asyncio
        result = asyncio.run(notifier.send("test", force=False))
        assert result is False

    def test_silent_hours_cross_midnight(self, monkeypatch):
        """Test cross-midnight silent hours logic."""
        from datetime import datetime
        from src.config import get_config

        config = get_config()
        monkeypatch.setattr(config.telegram, "silent_hours", (23, 7))

        notifier = TelegramNotifier()

        # Mock datetime.now() at 2am → should be silent
        # Hour 2 with silent_hours=(23, 7): start(23) > end(7) -> hour >= 23 or hour < 7
        # 2 >= 23 = False, 2 < 7 = True -> silent

        class MockDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 5, 20, 2, 0, 0)

        monkeypatch.setattr("src.services.notification.telegram.datetime", MockDatetime)
        assert notifier._in_silent_hours() is True

        class MockDatetime2(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 5, 20, 12, 0, 0)

        monkeypatch.setattr("src.services.notification.telegram.datetime", MockDatetime2)
        assert notifier._in_silent_hours() is False
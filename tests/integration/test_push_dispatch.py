"""Integration tests for push dispatch pipeline."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from src.contracts.push_event import PushEventType
from src.services.event_bus import EventBus, PushEvent
from src.services.push_adapters.telegram_stub import TelegramStubAdapter
from src.services.push_dispatcher import PushDispatcher
from src.services.rate_limiter import RateLimiter


@pytest.fixture
def tmp_db() -> str:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    conn = sqlite3.connect(db_path)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS push_dedup (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            pushed_at TEXT NOT NULL,
            channel TEXT NOT NULL
        )"""
    )
    conn.commit()
    conn.close()
    yield db_path
    Path(db_path).unlink(missing_ok=True)


def make_event(
    event_id: str = "evt-001",
    push_type: str = PushEventType.DECISION_GENERATED.value,
) -> PushEvent:
    return PushEvent(
        event_id=event_id,
        push_type=push_type,
        title="Test Event",
        body_markdown="Test body",
        related_symbols=["AAPL"],
    )


class TestPushDispatchIntegration:
    async def test_dedup_integration(self, tmp_db):
        """Publish two events with same event_id → only one should be delivered."""
        bus = EventBus()
        await bus.start()

        telegram = TelegramStubAdapter()
        dispatcher = PushDispatcher(
            adapters={"telegram": telegram},
            db_path=tmp_db,
        )
        bus.subscribe("PushEvent", dispatcher.dispatch)

        event1 = make_event(event_id="integ-dup-001")
        event2 = make_event(event_id="integ-dup-001")

        bus.publish(event1)
        bus.publish(event2)

        # let dispatch loop process
        import asyncio
        await asyncio.sleep(0.1)

        # verify dedup table has exactly 1 record
        conn = sqlite3.connect(tmp_db)
        count = conn.execute(
            "SELECT COUNT(*) FROM push_dedup WHERE event_id = ?", ("integ-dup-001",)
        ).fetchone()[0]
        conn.close()
        assert count == 1

        await bus.stop()

    async def test_rate_limit_integration(self, tmp_db):
        """Publish 11 events → 10 allowed, 11th rate-limited."""
        bus = EventBus()
        await bus.start()

        rl = RateLimiter(per_minute=10, per_hour=100)
        telegram = TelegramStubAdapter()
        dispatcher = PushDispatcher(
            adapters={"telegram": telegram},
            db_path=tmp_db,
            rate_limiter=rl,
        )
        bus.subscribe("PushEvent", dispatcher.dispatch)

        for i in range(11):
            bus.publish(make_event(event_id=f"integ-rl-{i:03d}"))

        import asyncio
        await asyncio.sleep(0.1)

        # 10 should be in dedup, 11th rate-limited (not persisted)
        conn = sqlite3.connect(tmp_db)
        count = conn.execute("SELECT COUNT(*) FROM push_dedup").fetchone()[0]
        conn.close()
        assert count == 10

        await bus.stop()

    async def test_non_push_event_ignored(self, tmp_db):
        """Non-PushEvent should be silently ignored."""
        bus = EventBus()
        await bus.start()

        from src.services.event_bus import BaseEvent

        telegram = TelegramStubAdapter()
        dispatcher = PushDispatcher(
            adapters={"telegram": telegram},
            db_path=tmp_db,
        )
        bus.subscribe("PushEvent", dispatcher.dispatch)

        bus.publish(BaseEvent())

        import asyncio
        await asyncio.sleep(0.1)

        conn = sqlite3.connect(tmp_db)
        count = conn.execute("SELECT COUNT(*) FROM push_dedup").fetchone()[0]
        conn.close()
        assert count == 0

        await bus.stop()

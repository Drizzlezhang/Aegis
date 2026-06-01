"""Integration test: full signal pipeline (adapter → collector → DB → EventBus → API)."""

from __future__ import annotations

import asyncio
import sqlite3
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from src.contracts.signal_event import (
    SignalEvent,
    SignalSentiment,
    SignalSource,
    SignalType,
)
from src.services.event_bus import EventBus, SignalReceivedEvent
from src.services.signal_collector import SignalCollector


# ── Fake adapters ────────────────────────────────────────────────────────────


class FakePolymarketAdapter(SignalSource):
    source_id = "polymarket"
    fetch_interval_seconds = 300

    async def fetch_latest(self) -> list[SignalEvent]:
        return [
            SignalEvent(
                id="fake-poly-001", source="polymarket",
                signal_type=SignalType.POLYMARKET_PROBABILITY,
                timestamp=datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC),
                symbols=["AAPL"], sentiment=SignalSentiment.BULLISH,
                confidence=0.72, title="AAPL to $200",
                content="Market expects AAPL rally",
                raw_url="https://polymarket.com/event/fake",
                metadata={"yes_price": 0.72},
            )
        ]

    async def health_check(self) -> bool:
        return True


class FakeXAdapter(SignalSource):
    source_id = "x"
    fetch_interval_seconds = 600

    async def fetch_latest(self) -> list[SignalEvent]:
        return [
            SignalEvent(
                id="fake-x-001", source="x",
                signal_type=SignalType.X_SOCIAL_POST,
                timestamp=datetime(2026, 6, 1, 12, 1, 0, tzinfo=UTC),
                symbols=["TSLA"], sentiment=SignalSentiment.BEARISH,
                confidence=0.60, title="TSLA looking weak",
                content="Sell signal on TSLA",
                raw_url="https://x.com/fake/1",
                metadata={"username": "trader1"},
            )
        ]

    async def health_check(self) -> bool:
        return True


class FakeMacroAdapter(SignalSource):
    source_id = "macro_news"
    fetch_interval_seconds = 900

    async def fetch_latest(self) -> list[SignalEvent]:
        return [
            SignalEvent(
                id="fake-macro-001", source="macro_news",
                signal_type=SignalType.MACRO_NEWS,
                timestamp=datetime(2026, 6, 1, 12, 2, 0, tzinfo=UTC),
                symbols=[], sentiment=SignalSentiment.NEUTRAL,
                confidence=0.35, title="Fed holds rates steady",
                content="Federal Reserve maintains current rate",
                raw_url="https://example.com/fed",
                metadata={"tone": 0.5},
            )
        ]

    async def health_check(self) -> bool:
        return True


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def temp_db():
    db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False, dir=".")
    db_path = db_file.name
    db_file.close()
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS signal_events (
                id TEXT PRIMARY KEY, source TEXT NOT NULL,
                signal_type TEXT NOT NULL, timestamp TEXT NOT NULL,
                symbols TEXT NOT NULL, sentiment TEXT NOT NULL,
                confidence REAL NOT NULL, title TEXT NOT NULL,
                content TEXT NOT NULL, raw_url TEXT, metadata TEXT
            )
        """)
    yield db_path
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def fake_sources():
    return [FakePolymarketAdapter(), FakeXAdapter(), FakeMacroAdapter()]


@pytest.fixture
async def event_bus():
    bus = EventBus()
    await bus.start()
    yield bus
    await bus.stop()


@pytest.fixture
def collector(fake_sources, temp_db, event_bus):
    coll = SignalCollector(sources=fake_sources, db_path=temp_db)
    coll._bus = event_bus
    return coll


# ── Tests ────────────────────────────────────────────────────────────────────


class TestSignalPipeline:
    async def test_collector_inserts_into_db(self, collector, temp_db):
        count = await collector.run_once()
        assert count == 3
        with sqlite3.connect(temp_db) as conn:
            rows = conn.execute("SELECT COUNT(*) FROM signal_events").fetchone()
            assert rows[0] == 3

    async def test_collector_publishes_events(self, collector, event_bus):
        received: list[SignalReceivedEvent] = []

        async def handler(event):
            received.append(event)

        event_bus.subscribe("SignalReceivedEvent", handler)
        await collector.run_once()
        await asyncio.sleep(0.1)

        assert len(received) == 3
        for evt in received:
            assert evt.signal is not None
            assert isinstance(evt.signal, SignalEvent)

    async def test_collector_idempotent(self, collector, temp_db):
        await collector.run_once()
        await collector.run_once()
        with sqlite3.connect(temp_db) as conn:
            rows = conn.execute("SELECT COUNT(*) FROM signal_events").fetchone()
            assert rows[0] == 3

    async def test_api_returns_data(self, collector, temp_db):
        await collector.run_once()

        # Patch config to use temp DB, then use real get_session
        with patch("src.db.get_config") as mock_cfg:
            mock_cfg.return_value.database.url = f"sqlite:///{temp_db}"
            mock_cfg.return_value.database.pool_size = 1
            mock_cfg.return_value.database.max_overflow = 0
            mock_cfg.return_value.database.echo = False

            # Reset engine cache so it picks up new URL
            import src.db
            src.db._engine = None
            src.db._session_factory = None

            from src.api.routes.signals import list_signals
            response = await list_signals()
            assert response["total"] == 3
            assert len(response["items"]) == 3
            assert response["has_more"] is False

    async def test_api_no_mock_field(self, collector, temp_db):
        await collector.run_once()

        with patch("src.db.get_config") as mock_cfg:
            mock_cfg.return_value.database.url = f"sqlite:///{temp_db}"
            mock_cfg.return_value.database.pool_size = 1
            mock_cfg.return_value.database.max_overflow = 0
            mock_cfg.return_value.database.echo = False

            import src.db
            src.db._engine = None
            src.db._session_factory = None

            from src.api.routes.signals import list_signals
            response = await list_signals()
            assert "_mock" not in response

    async def test_api_filter_by_source(self, collector, temp_db):
        await collector.run_once()

        with patch("src.db.get_config") as mock_cfg:
            mock_cfg.return_value.database.url = f"sqlite:///{temp_db}"
            mock_cfg.return_value.database.pool_size = 1
            mock_cfg.return_value.database.max_overflow = 0
            mock_cfg.return_value.database.echo = False

            import src.db
            src.db._engine = None
            src.db._session_factory = None

            from src.api.routes.signals import list_signals
            response = await list_signals(source="polymarket")
            assert response["total"] == 1
            assert response["items"][0]["source"] == "polymarket"

    async def test_api_filter_by_sentiment(self, collector, temp_db):
        await collector.run_once()

        with patch("src.db.get_config") as mock_cfg:
            mock_cfg.return_value.database.url = f"sqlite:///{temp_db}"
            mock_cfg.return_value.database.pool_size = 1
            mock_cfg.return_value.database.max_overflow = 0
            mock_cfg.return_value.database.echo = False

            import src.db
            src.db._engine = None
            src.db._session_factory = None

            from src.api.routes.signals import list_signals
            response = await list_signals(sentiment="bullish")
            assert response["total"] == 1
            assert response["items"][0]["sentiment"] == "bullish"

    async def test_api_empty_when_no_data(self, temp_db):
        with patch("src.db.get_config") as mock_cfg:
            mock_cfg.return_value.database.url = f"sqlite:///{temp_db}"
            mock_cfg.return_value.database.pool_size = 1
            mock_cfg.return_value.database.max_overflow = 0
            mock_cfg.return_value.database.echo = False

            import src.db
            src.db._engine = None
            src.db._session_factory = None

            from src.api.routes.signals import list_signals
            response = await list_signals()
            assert response == {"items": [], "total": 0, "has_more": False}
            assert "_mock" not in response

    async def test_health_check_all_adapters(self, fake_sources):
        for source in fake_sources:
            assert await source.health_check() is True

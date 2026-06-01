"""SignalCollector — schedules signal sources, persists events, publishes to EventBus."""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from pathlib import Path

from src.config import get_config
from src.contracts.signal_event import SignalEvent, SignalSource
from src.services.event_bus import SignalReceivedEvent, get_event_bus

logger = logging.getLogger(__name__)


class SignalCollector:
    """Manages multiple SignalSources, each on its own fetch interval.

    Fetched SignalEvents are inserted into the ``signal_events`` table
    (ON CONFLICT DO NOTHING) and published as ``SignalReceivedEvent``
    on the EventBus.
    """

    def __init__(
        self,
        sources: list[SignalSource],
        db_path: str | Path | None = None,
    ) -> None:
        self._sources = sources
        config = get_config()
        self._db_path = Path(db_path or config.memory.sqlite_path).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._bus = get_event_bus()
        self._tasks: list[asyncio.Task[None]] = []

    async def start(self) -> None:
        """Start one background task per signal source."""
        for source in self._sources:
            task = asyncio.create_task(self._run_source(source))
            self._tasks.append(task)
        logger.info("SignalCollector: started %d source(s)", len(self._sources))

    async def stop(self) -> None:
        """Cancel all background tasks."""
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("SignalCollector: stopped")

    async def run_once(self) -> int:
        """Fetch all sources once (useful for testing). Returns total events collected."""
        total = 0
        for source in self._sources:
            try:
                events = await source.fetch_latest()
                for event in events:
                    self._insert_event(event)
                    self._bus.publish(SignalReceivedEvent(signal=event))
                total += len(events)
            except Exception:
                logger.exception("SignalCollector: source %s failed", source.source_id)
        return total

    async def _run_source(self, source: SignalSource) -> None:
        while True:
            try:
                events = await source.fetch_latest()
                for event in events:
                    self._insert_event(event)
                    self._bus.publish(SignalReceivedEvent(signal=event))
                if events:
                    logger.info(
                        "SignalCollector: %s fetched %d event(s)",
                        source.source_id,
                        len(events),
                    )
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("SignalCollector: source %s failed", source.source_id)
            await asyncio.sleep(source.fetch_interval_seconds)

    def _insert_event(self, event: SignalEvent) -> None:
        """Insert a SignalEvent into the signal_events table (idempotent)."""
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO signal_events
                    (id, source, signal_type, timestamp, symbols, sentiment,
                     confidence, title, content, raw_url, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.source,
                    event.signal_type.value,
                    event.timestamp.isoformat(),
                    json.dumps(event.symbols),
                    event.sentiment.value,
                    event.confidence,
                    event.title,
                    event.content,
                    event.raw_url,
                    json.dumps(event.metadata),
                ),
            )

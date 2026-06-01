"""Push dispatcher — subscribes to EventBus PushEvent, dedup → rate-limit → route → persist."""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from src.contracts.push_event import PushEventType
from src.services.event_bus import BaseEvent, PushEvent
from src.services.push_adapters.base import PushAdapter
from src.services.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# Route table: push_type → set of adapter names
_ROUTE_TABLE: dict[str, set[str]] = {
    PushEventType.DECISION_GENERATED.value: {"telegram", "websocket"},
    PushEventType.SIGNAL_RECEIVED.value: {"websocket"},
    PushEventType.PHASE_TRANSITION.value: {"telegram"},
    PushEventType.SYSTEM_HEALTH.value: {"telegram"},
}


class PushDispatcher:
    """Orchestrates push event processing: dedup → rate-limit → route → persist."""

    def __init__(
        self,
        adapters: dict[str, PushAdapter],
        db_path: str | Path,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self._adapters = adapters
        self._db_path = Path(db_path)
        self._rate_limiter = rate_limiter or RateLimiter()

    async def dispatch(self, event: BaseEvent) -> None:
        if not isinstance(event, PushEvent):
            return

        # 1. Dedup
        if self._is_duplicate(event.event_id):
            logger.debug("PushDispatcher: duplicate event %s, skipping", event.event_id)
            return

        # 2. Rate limit
        if not self._rate_limiter.check(event.push_type):
            logger.warning(
                "PushDispatcher: rate limited push_type=%s event_id=%s",
                event.push_type,
                event.event_id,
            )
            return

        # 3. Route
        targets = _ROUTE_TABLE.get(event.push_type, set())
        if not targets:
            logger.warning(
                "PushDispatcher: unknown push_type=%s event_id=%s",
                event.push_type,
                event.event_id,
            )
            return

        for name in targets:
            adapter = self._adapters.get(name)
            if adapter is None:
                logger.warning("PushDispatcher: adapter %s not configured", name)
                continue
            try:
                await adapter.send(event)
            except Exception:
                logger.exception(
                    "PushDispatcher: adapter %s failed for event_id=%s",
                    name,
                    event.event_id,
                )

        # 4. Persist dedup record
        self._persist_dedup(event)

    # ── internal ────────────────────────────────────────────────────────

    def _is_duplicate(self, event_id: str) -> bool:
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                row = conn.execute(
                    "SELECT 1 FROM push_dedup WHERE event_id = ?", (event_id,)
                ).fetchone()
                return row is not None
        except sqlite3.OperationalError:
            # table may not exist yet (first run before migration)
            return False
        except Exception:
            logger.exception("PushDispatcher: dedup check failed for %s", event_id)
            return False

    def _persist_dedup(self, event: PushEvent) -> None:
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.execute(
                    "INSERT INTO push_dedup (event_id, event_type, pushed_at, channel) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        event.event_id,
                        event.push_type,
                        datetime.now(UTC).isoformat(),
                        ",".join(sorted(_ROUTE_TABLE.get(event.push_type, set()))),
                    ),
                )
                conn.commit()
        except sqlite3.IntegrityError:
            logger.debug("PushDispatcher: event_id=%s already in dedup", event.event_id)
        except Exception:
            logger.exception("PushDispatcher: failed to persist dedup for %s", event.event_id)

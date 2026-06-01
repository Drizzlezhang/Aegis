"""Decision Composer — assembles DecisionContext from signals + Wyckoff phase."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from src.contracts.decision_context import DecisionContext
from src.contracts.signal_event import SignalEvent
from src.services.signal_fusion import SignalFusionEngine

logger = logging.getLogger(__name__)


class DecisionComposer:
    """Assembles a DecisionContext from signals, Wyckoff phase, and market data.

    On each compose() call:
    1. Fuses signals via SignalFusionEngine
    2. Builds a DecisionContext
    3. Optionally publishes a DecisionGeneratedEvent via EventBus
    """

    def __init__(self, fusion: SignalFusionEngine, event_bus=None):
        """Args:
            fusion: SignalFusionEngine instance.
            event_bus: Optional EventBus instance. If None, event publishing is skipped.
        """
        self._fusion = fusion
        self._event_bus = event_bus

    async def compose(
        self,
        symbol: str,
        wyckoff_phase: str,
        current_price: float | None,
        watchlist_position: dict,
        signals: list[SignalEvent],
    ) -> DecisionContext:
        """Compose a full DecisionContext.

        Args:
            symbol: Ticker symbol (e.g. "AAPL").
            wyckoff_phase: Current Wyckoff phase string.
            current_price: Latest price or None.
            watchlist_position: Virtual position snapshot dict.
            signals: List of SignalEvents to fuse.

        Returns:
            DecisionContext ready for persistence and trace.
        """
        fused = await self._fusion.fuse_with_explanation(signals)

        context = DecisionContext(
            symbol=symbol,
            timestamp=datetime.now(UTC),
            wyckoff_phase=wyckoff_phase,
            current_price=current_price,
            watchlist_position=watchlist_position,
            signal_events=signals,
            fused_signal=fused,
            context_snapshot={
                "wyckoff_phase": wyckoff_phase,
                "signal_count": len(signals),
                "has_conflict": fused.has_conflict,
                "conflict_axis": fused.conflict_axis,
            },
        )

        # Publish event for downstream subscribers (e.g. D branch push)
        if self._event_bus is not None:
            try:
                from src.services.event_bus import DecisionGeneratedEvent

                event = DecisionGeneratedEvent(
                    decision_id="",  # filled after persistence
                    symbol=symbol,
                    context=context,
                )
                self._event_bus.publish(event)
            except Exception:
                logger.exception("Failed to publish DecisionGeneratedEvent")

        return context

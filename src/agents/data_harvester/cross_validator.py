"""Multi-source cross validation — detect price discrepancies across data providers."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from statistics import median
from typing import TYPE_CHECKING

from src.services.event_bus import BaseEvent, EventSeverity

if TYPE_CHECKING:
    from src.services.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class DataDiscrepancy(BaseEvent):
    """Emitted when close price deviation exceeds threshold across sources."""

    symbol: str = ""
    source_1: str = ""
    source_2: str = ""
    value_1: float = 0.0
    value_2: float = 0.0
    deviation_pct: float = 0.0
    median_value: float = 0.0
    severity: EventSeverity = EventSeverity.WARNING


class CrossValidator:
    """Validate OHLCV data across multiple sources.

    When >= 2 sources are available for the same symbol, compares close prices.
    If deviation exceeds threshold, emits a DataDiscrepancy event via EventBus.
    Returns merged data with median close values (3+ sources) or the primary
    source's data (2 sources with warning).
    """

    def __init__(
        self,
        threshold: float = 0.005,
        event_bus: EventBus | None = None,
    ):
        self._threshold = threshold
        self._event_bus = event_bus

    def validate(
        self, symbol: str, sources: dict[str, dict]
    ) -> dict:
        """Cross-validate OHLCV data from multiple sources.

        Args:
            symbol: The trading symbol.
            sources: Dict of {provider_name: ohlcv_dict}.

        Returns:
            Merged OHLCV dict with median close values (3+ sources) or
            primary source data (2 sources).
        """
        if len(sources) < 2:
            # Single source — no validation needed
            return list(sources.values())[0] if sources else {}

        # Extract close prices from each source
        close_prices: dict[str, float] = {}
        for name, data in sources.items():
            close_val = self._extract_close(data)
            if close_val is not None:
                close_prices[name] = close_val

        if len(close_prices) < 2:
            return list(sources.values())[0] if sources else {}

        # Check pairwise deviations
        source_names = list(close_prices.keys())
        for i in range(len(source_names)):
            for j in range(i + 1, len(source_names)):
                n1, n2 = source_names[i], source_names[j]
                v1, v2 = close_prices[n1], close_prices[n2]
                if v2 == 0:
                    continue
                deviation = abs(v1 - v2) / abs(v2)
                if deviation > self._threshold:
                    med = median(close_prices.values())
                    event = DataDiscrepancy(
                        symbol=symbol,
                        source_1=n1,
                        source_2=n2,
                        value_1=v1,
                        value_2=v2,
                        deviation_pct=round(deviation, 6),
                        median_value=med,
                    )
                    logger.warning(
                        f"Data discrepancy: {symbol} {n1}={v1} vs {n2}={v2} "
                        f"(deviation={deviation:.4%}, median={med})"
                    )
                    if self._event_bus:
                        self._event_bus.publish(event)

        # Merge: use median close if 3+ sources, otherwise primary source
        if len(close_prices) >= 3:
            med = median(close_prices.values())
            merged = dict(list(sources.values())[0])  # Copy structure from first
            merged["close"] = med
            return merged
        else:
            # 2 sources: return primary, deviation already warned
            return list(sources.values())[0]

    @staticmethod
    def _extract_close(data: dict) -> float | None:
        """Extract the latest close price from OHLCV data."""
        if not data:
            return None
        close = data.get("close")
        if close is None:
            return None
        if isinstance(close, (int, float)):
            return float(close)
        if isinstance(close, list) and len(close) > 0:
            return float(close[-1])
        return None

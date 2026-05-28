"""Data gap detection — scan OHLCV sequences for timestamp discontinuities."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from src.services.event_bus import BaseEvent, EventSeverity

if TYPE_CHECKING:
    from src.services.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class DataGapEvent(BaseEvent):
    """Emitted when a gap is detected in OHLCV time series."""

    symbol: str = ""
    gap_start: str = ""       # ISO date string
    gap_end: str = ""         # ISO date string
    gap_bars: int = 0
    severity: EventSeverity = EventSeverity.WARNING


class GapDetector:
    """Detect gaps in OHLCV time series data.

    Scans the "date" field of OHLCV records for discontinuities.
    Skips weekends (Saturday/Sunday). Emits DataGapEvent via EventBus
    when gaps exceed the configured threshold.
    """

    def __init__(
        self,
        threshold_bars: int = 1,
        event_bus: EventBus | None = None,
    ):
        self._threshold_bars = threshold_bars
        self._event_bus = event_bus

    def detect(
        self, symbol: str, ohlcv_data: list[dict]
    ) -> list[DataGapEvent]:
        """Scan OHLCV data for timestamp gaps.

        Args:
            symbol: The trading symbol.
            ohlcv_data: List of OHLCV records, each with a "date" field.

        Returns:
            List of DataGapEvent for each detected gap.
        """
        if len(ohlcv_data) < 2:
            return []

        dates = self._parse_dates(ohlcv_data)
        if len(dates) < 2:
            return []

        gaps: list[DataGapEvent] = []
        for i in range(1, len(dates)):
            prev_date = dates[i - 1]
            curr_date = dates[i]

            trading_days = self._trading_days_between(prev_date, curr_date)
            if trading_days >= self._threshold_bars:
                gap = DataGapEvent(
                    symbol=symbol,
                    gap_start=prev_date.isoformat(),
                    gap_end=curr_date.isoformat(),
                    gap_bars=trading_days,
                )
                gaps.append(gap)
                logger.warning(
                    f"Data gap detected: {symbol} {gap.gap_start} → {gap.gap_end} "
                    f"({trading_days} trading days missing)"
                )
                if self._event_bus:
                    self._event_bus.publish(gap)

        return gaps

    @staticmethod
    def _parse_dates(ohlcv_data: list[dict]) -> list[date]:
        """Extract and parse date fields from OHLCV records."""
        result: list[date] = []
        for record in ohlcv_data:
            d = record.get("date") or record.get("Date") or record.get("timestamp")
            if d is None:
                continue
            if isinstance(d, date):
                result.append(d)
            elif isinstance(d, datetime):
                result.append(d.date())
            elif isinstance(d, str):
                # Try common formats
                for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y%m%d"):
                    try:
                        result.append(datetime.strptime(d[:10], fmt).date())
                        break
                    except ValueError:
                        continue
                else:
                    # Last resort: try ISO format
                    try:
                        result.append(date.fromisoformat(d[:10]))
                    except (ValueError, TypeError):
                        continue
        return result

    @staticmethod
    def _is_weekend(d: date) -> bool:
        """Return True if date is Saturday (5) or Sunday (6)."""
        return d.weekday() >= 5

    @staticmethod
    def _trading_days_between(d1: date, d2: date) -> int:
        """Count trading days (Mon-Fri) between two dates, exclusive of both.

        Example:
            Friday → Monday: 0 trading days between (weekend skipped)
            Monday → Wednesday: 1 trading day between (Tuesday)
        """
        if d2 <= d1:
            return 0

        count = 0
        current = d1 + timedelta(days=1)
        while current < d2:
            if not GapDetector._is_weekend(current):
                count += 1
            current += timedelta(days=1)
        return count

"""Phase dimension failure event — lightweight dataclass for internal diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class PhaseDimensionFailure:
    """Records a dimension scoring failure during predict().

    Stored in PhasePredictor._events list for per-call diagnostics.
    Not published to the global EventBus (see ADR-1).
    """

    dim_name: str
    error_message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

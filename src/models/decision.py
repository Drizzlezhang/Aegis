"""Decision log models."""

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field


class DecisionType(StrEnum):
    OPEN = "open"
    CLOSE = "close"
    TRIM = "trim"
    ADD = "add"
    ROLL = "roll"
    HOLD = "hold"
    SKIP = "skip"


class DecisionOutcome(StrEnum):
    PENDING = "pending"
    PROFITABLE = "profitable"
    LOSS = "loss"
    BREAKEVEN = "breakeven"
    EXPIRED = "expired"


class DecisionEntry(BaseModel):
    id: str = Field(..., description="Unique decision ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    symbol: str
    decision_type: DecisionType
    current_price: float
    technical_score: float | None = None
    macro_regime: str | None = None
    strategy_name: str | None = None
    confidence: float = Field(0.0, ge=0, le=1)
    reasoning: str = ""
    contract_symbol: str | None = None
    entry_price: float | None = None
    quantity: int = 0
    stop_loss: float | None = None
    profit_target: float | None = None
    outcome: DecisionOutcome = DecisionOutcome.PENDING
    actual_pnl: float | None = None
    reflection: str | None = None
    reflection_date: datetime | None = None

"""Decision tracking data models."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class TrackingStatus(StrEnum):
    PENDING = "pending"          # freshly recommended, awaiting verification
    ACTIVE = "active"            # within holding period, price not triggered
    HIT_TARGET = "hit_target"    # take-profit target reached
    HIT_STOP = "hit_stop"        # stop-loss triggered
    EXPIRED = "expired"          # expired without trigger


class TrackedDecision(BaseModel):
    id: str
    symbol: str
    strategy_type: str
    recommended_at: datetime
    entry_price: float
    target_price: float | None = None
    stop_loss_price: float | None = None
    expiry_date: datetime | None = None
    confidence: float
    status: TrackingStatus = TrackingStatus.PENDING
    actual_high: float | None = None
    actual_low: float | None = None
    actual_price_at_expiry: float | None = None
    hit_date: datetime | None = None
    pnl_pct: float | None = None
    updated_at: datetime | None = None

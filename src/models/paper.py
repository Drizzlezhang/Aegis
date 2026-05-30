"""Paper trading data models."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class OrderStatus(StrEnum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class Order(BaseModel):
    """A paper trading order."""

    id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int = Field(gt=0)
    limit_price: float | None = None
    stop_price: float | None = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    filled_avg_price: float | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    cancelled_at: datetime | None = None
    rejection_reason: str | None = None


class OrderResult(BaseModel):
    """Result of placing an order."""

    success: bool
    order_id: str
    message: str = ""


class PositionSnapshot(BaseModel):
    """Snapshot of a single position."""

    symbol: str
    quantity: int
    avg_cost: float
    market_price: float | None = None
    unrealized_pnl: float | None = None
    unrealized_pnl_pct: float | None = None


class AccountSnapshot(BaseModel):
    """Snapshot of account balance."""

    cash: float
    equity: float
    buying_power: float
    positions: list[PositionSnapshot] = Field(default_factory=list)
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0

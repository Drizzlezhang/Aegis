"""Position tracking models."""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field

from .options import OptionContract
from .plan import TradePlan


class PositionStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    ROLLED = "rolled"
    CLOSED = "closed"
    EXPIRED = "expired"


class PositionAction(BaseModel):
    action_type: str
    date: date
    price: float
    quantity: int = 1
    notes: str = ""


class Position(BaseModel):
    id: str
    symbol: str
    contract: OptionContract
    status: PositionStatus = PositionStatus.PLANNED
    entry_price: float
    current_price: float | None = None
    quantity: int = 1
    entry_date: date
    close_date: date | None = None
    trade_plan: TradePlan | None = None
    actions: list[PositionAction] = Field(default_factory=list)
    notes: str = ""

    @property
    def unrealized_pnl(self) -> float | None:
        if self.current_price is not None:
            return (self.current_price - self.entry_price) * self.quantity * 100
        return None

    @property
    def unrealized_pnl_pct(self) -> float | None:
        if self.current_price is not None and self.entry_price > 0:
            return ((self.current_price - self.entry_price) / self.entry_price) * 100
        return None

    @property
    def days_held(self) -> int:
        end = self.close_date or date.today()
        return (end - self.entry_date).days

    @property
    def dte_remaining(self) -> int:
        return self.contract.days_to_expiry

"""Options data models."""

from typing import List, Dict, Optional
from datetime import datetime, date
from pydantic import BaseModel
from enum import Enum

from .market import OHLCV


class OptionType(str, Enum):
    """Option type enumeration."""
    CALL = "call"
    PUT = "put"


class OptionContract(BaseModel):
    """Option contract data model."""
    symbol: str
    underlying: str
    contract_symbol: str
    strike: float
    expiry: date
    option_type: OptionType
    last_price: float | None = None
    bid: float | None = None
    ask: float | None = None
    volume: int | None = None
    open_interest: int | None = None
    implied_volatility: float | None = None
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None
    rho: float | None = None

    @property
    def days_to_expiry(self) -> int:
        """Calculate days to expiry."""
        return (self.expiry - date.today()).days

    @property
    def is_leaps(self) -> bool:
        """Check if this is a LEAPS option (>= 10 months)."""
        return self.days_to_expiry >= 300

    @property
    def mid_price(self) -> float | None:
        """Calculate mid price."""
        if self.bid is not None and self.ask is not None:
            return (self.bid + self.ask) / 2
        return self.last_price


class OptionChain(BaseModel):
    """Option chain data model."""
    symbol: str
    timestamp: datetime
    spot_price: float
    calls: List[OptionContract]
    puts: List[OptionContract]
    expiry_dates: List[date]

    def get_contracts_by_expiry(self, expiry: date) -> Dict[OptionType, List[OptionContract]]:
        """Get contracts by expiry date."""
        return {
            OptionType.CALL: [c for c in self.calls if c.expiry == expiry],
            OptionType.PUT: [p for p in self.puts if p.expiry == expiry]
        }

    def get_nearest_expiry(self, min_days: int = 0) -> date | None:
        """Get nearest expiry date with at least min_days."""
        today = date.today()
        valid_expiries = [expiry for expiry in self.expiry_dates if (expiry - today).days >= min_days]
        return min(valid_expiries) if valid_expiries else None

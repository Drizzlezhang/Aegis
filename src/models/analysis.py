"""Analysis data models."""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, field_validator


class VolumeProfile(BaseModel):
    """Volume profile data model."""
    symbol: str
    timestamp: datetime
    price_bins: List[float]
    volume_bins: List[float]
    poc_price: float  # Point of Control
    vah_price: float  # Value Area High
    val_price: float  # Value Area Low
    total_volume: float

    @property
    def value_area_range(self) -> float:
        """Calculate value area range."""
        return self.vah_price - self.val_price

    @property
    def poc_percentage(self) -> float:
        """Calculate POC volume percentage."""
        poc_index = self.price_bins.index(self.poc_price)
        poc_volume = self.volume_bins[poc_index]
        return (poc_volume / self.total_volume) * 100


class GEXWall(BaseModel):
    """GEX Wall data model."""
    symbol: str
    timestamp: datetime
    strike: float
    net_gex: float
    wall_type: str  # "support" | "resistance"
    call_gex: float
    put_gex: float
    open_interest: int

    @property
    def absolute_gex(self) -> float:
        """Get absolute GEX value."""
        return abs(self.net_gex)

    @property
    def is_support(self) -> bool:
        """Check if this is a support wall."""
        return self.wall_type == "support"

    @property
    def is_resistance(self) -> bool:
        """Check if this is a resistance wall."""
        return self.wall_type == "resistance"


class SupportResistanceLevel(BaseModel):
    """Support/Resistance level data model."""
    price: float
    level_type: str  # "support" | "resistance"
    confidence: float  # 0.0 to 1.0
    source: str  # "volume_profile", "gex", "prior", "technical"
    description: str | None = None

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Validate confidence is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("confidence must be between 0 and 1")
        return v


class ValuationRange(BaseModel):
    """Valuation range data model."""
    symbol: str
    timestamp: datetime
    current_price: float
    low_estimate: float
    fair_estimate: float
    high_estimate: float
    method: str  # "pe_band", "dcf", "multi_factor", "comps"
    confidence: float
    pe_percentile: float | None = None
    forward_pe: float | None = None

    @property
    def is_undervalued(self) -> bool:
        """Check if current price is below fair estimate."""
        return self.current_price < self.fair_estimate * 0.95

    @property
    def is_overvalued(self) -> bool:
        """Check if current price is above fair estimate."""
        return self.current_price > self.fair_estimate * 1.05

    @property
    def discount_to_fair(self) -> float:
        """Calculate discount to fair value."""
        return ((self.fair_estimate - self.current_price) / self.fair_estimate) * 100

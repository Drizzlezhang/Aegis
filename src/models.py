"""Data models for Aegis-Trader."""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime, date
from pydantic import BaseModel, Field, validator
from enum import Enum
import pandas as pd


class AssetType(str, Enum):
    """Asset type enumeration."""
    STOCK = "stock"
    ETF = "etf"
    OPTION = "option"
    INDEX = "index"


class OptionType(str, Enum):
    """Option type enumeration."""
    CALL = "call"
    PUT = "put"


class OHLCV(BaseModel):
    """OHLCV data model."""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    adjusted_close: Optional[float] = None

    class Config:
        arbitrary_types_allowed = True

    def to_dataframe(self) -> pd.DataFrame:
        """Convert to pandas DataFrame."""
        return pd.DataFrame([self.dict()])

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame, symbol: str) -> List["OHLCV"]:
        """Create from pandas DataFrame."""
        ohlcv_list = []
        for _, row in df.iterrows():
            ohlcv = cls(
                symbol=symbol,
                timestamp=row.get("timestamp") or row.get("date") or row.get("Date"),
                open=float(row.get("open") or row.get("Open")),
                high=float(row.get("high") or row.get("High")),
                low=float(row.get("low") or row.get("Low")),
                close=float(row.get("close") or row.get("Close")),
                volume=int(row.get("volume") or row.get("Volume")),
                adjusted_close=float(row.get("adjusted_close") or row.get("Adj Close")) if "adjusted_close" in row or "Adj Close" in row else None
            )
            ohlcv_list.append(ohlcv)
        return ohlcv_list


class OptionContract(BaseModel):
    """Option contract data model."""
    symbol: str
    underlying: str
    contract_symbol: str
    strike: float
    expiry: date
    option_type: OptionType
    last_price: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume: Optional[int] = None
    open_interest: Optional[int] = None
    implied_volatility: Optional[float] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None

    @property
    def days_to_expiry(self) -> int:
        """Calculate days to expiry."""
        return (self.expiry - date.today()).days

    @property
    def is_leaps(self) -> bool:
        """Check if this is a LEAPS option (>= 10 months)."""
        return self.days_to_expiry >= 300

    @property
    def mid_price(self) -> Optional[float]:
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

    def get_nearest_expiry(self, min_days: int = 0) -> Optional[date]:
        """Get nearest expiry date with at least min_days."""
        today = date.today()
        valid_expiries = [expiry for expiry in self.expiry_dates if (expiry - today).days >= min_days]
        return min(valid_expiries) if valid_expiries else None


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
    description: Optional[str] = None

    @validator("confidence")
    def validate_confidence(cls, v):
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
    pe_percentile: Optional[float] = None
    forward_pe: Optional[float] = None

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


class RecommendedOption(BaseModel):
    """Recommended option data model."""
    contract: OptionContract
    recommendation_type: str  # "leaps_call", "bull_spread", "covered_call"
    entry_price: float
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    confidence: float
    reasoning: str
    support_levels: List[SupportResistanceLevel] = Field(default_factory=list)

    @property
    def max_loss(self) -> Optional[float]:
        """Calculate maximum loss."""
        if self.stop_loss:
            return abs(self.entry_price - self.stop_loss)
        return None

    @property
    def potential_gain(self) -> Optional[float]:
        """Calculate potential gain."""
        if self.target_price:
            return self.target_price - self.entry_price
        return None


class AgentState(BaseModel):
    """Agent state data model."""
    symbol: str
    trade_date: date
    # Data-Harvester output
    ohlcv_data: Optional[List[OHLCV]] = None
    options_chain: Optional[OptionChain] = None
    youtube_signals: List[Dict[str, Any]] = Field(default_factory=list)
    # Quant-Brain output
    valuation_range: Optional[ValuationRange] = None
    support_levels: List[SupportResistanceLevel] = Field(default_factory=list)
    resistance_levels: List[SupportResistanceLevel] = Field(default_factory=list)
    volume_profile: Optional[VolumeProfile] = None
    gex_walls: List[GEXWall] = Field(default_factory=list)
    # Strategy-Exec output
    recommended_options: List[RecommendedOption] = Field(default_factory=list)
    action_report: str = ""
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.now)
    agent_sequence: List[str] = Field(default_factory=list)

    def add_agent_step(self, agent_name: str) -> None:
        """Add an agent step to the sequence."""
        self.agent_sequence.append(f"{agent_name}:{datetime.now().isoformat()}")

    def get_support_prices(self) -> List[float]:
        """Get all support prices sorted by confidence."""
        return sorted(
            [level.price for level in self.support_levels],
            key=lambda x: x
        )

    def get_resistance_prices(self) -> List[float]:
        """Get all resistance prices sorted by confidence."""
        return sorted(
            [level.price for level in self.resistance_levels],
            key=lambda x: x
        )


# Export all models
__all__ = [
    "AssetType",
    "OptionType",
    "OHLCV",
    "OptionContract",
    "OptionChain",
    "VolumeProfile",
    "GEXWall",
    "SupportResistanceLevel",
    "ValuationRange",
    "RecommendedOption",
    "AgentState",
]
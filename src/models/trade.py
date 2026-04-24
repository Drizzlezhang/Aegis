"""Trade recommendation and agent state models."""

from typing import List, Dict, Any, Optional
from datetime import datetime, date
from pydantic import BaseModel, Field

from .market import OHLCV
from .options import OptionContract, OptionChain
from .analysis import VolumeProfile, GEXWall, SupportResistanceLevel, ValuationRange


class RecommendedOption(BaseModel):
    """Recommended option data model."""
    contract: OptionContract
    recommendation_type: str  # "leaps_call", "bull_spread", "covered_call"
    entry_price: float
    target_price: float | None = None
    stop_loss: float | None = None
    risk_reward_ratio: float | None = None
    confidence: float
    reasoning: str
    support_levels: List[SupportResistanceLevel] = Field(default_factory=list)

    @property
    def max_loss(self) -> float | None:
        """Calculate maximum loss."""
        if self.stop_loss:
            return abs(self.entry_price - self.stop_loss)
        return None

    @property
    def potential_gain(self) -> float | None:
        """Calculate potential gain."""
        if self.target_price:
            return self.target_price - self.entry_price
        return None


class AgentState(BaseModel):
    """Agent state data model."""
    symbol: str
    trade_date: date
    # Data-Harvester output
    ohlcv_data: List[OHLCV] | None = None
    options_chain: OptionChain | None = None
    youtube_signals: List[Dict[str, Any]] = Field(default_factory=list)
    # Quant-Brain output
    valuation_range: ValuationRange | None = None
    support_levels: List[SupportResistanceLevel] = Field(default_factory=list)
    resistance_levels: List[SupportResistanceLevel] = Field(default_factory=list)
    volume_profile: VolumeProfile | None = None
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

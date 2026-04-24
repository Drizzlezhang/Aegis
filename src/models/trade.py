"""Trade recommendation and agent state models."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from .analysis import GEXWall, SupportResistanceLevel, ValuationRange, VolumeProfile
from .market import OHLCV
from .options import OptionChain, OptionContract


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
    support_levels: list[SupportResistanceLevel] = Field(default_factory=list)

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
    ohlcv_data: list[OHLCV] | None = None
    options_chain: OptionChain | None = None
    youtube_signals: list[dict[str, Any]] = Field(default_factory=list)
    # Quant-Brain output
    valuation_range: ValuationRange | None = None
    support_levels: list[SupportResistanceLevel] = Field(default_factory=list)
    resistance_levels: list[SupportResistanceLevel] = Field(default_factory=list)
    volume_profile: VolumeProfile | None = None
    gex_walls: list[GEXWall] = Field(default_factory=list)
    # Strategy-Exec output
    recommended_options: list[RecommendedOption] = Field(default_factory=list)
    action_report: str = ""
    # Quant-Brain enhanced report
    analysis_report: str = ""
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.now)
    agent_sequence: list[str] = Field(default_factory=list)

    def add_agent_step(self, agent_name: str) -> None:
        """Add an agent step to the sequence."""
        self.agent_sequence.append(f"{agent_name}:{datetime.now().isoformat()}")

    def get_support_prices(self) -> list[float]:
        """Get all support prices sorted by confidence."""
        return sorted(
            [level.price for level in self.support_levels],
            key=lambda x: x
        )

    def get_resistance_prices(self) -> list[float]:
        """Get all resistance prices sorted by confidence."""
        return sorted(
            [level.price for level in self.resistance_levels],
            key=lambda x: x
        )

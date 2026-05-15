"""Trade recommendation models."""

from pydantic import BaseModel, Field

from .analysis import SupportResistanceLevel
from .options import OptionContract

# Backward compatibility — AgentState moved to state.py
from .state import AgentState, QuantResult, StrategyResult  # noqa: F401


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
        if self.stop_loss:
            return abs(self.entry_price - self.stop_loss)
        return None

    @property
    def potential_gain(self) -> float | None:
        if self.target_price:
            return self.target_price - self.entry_price
        return None

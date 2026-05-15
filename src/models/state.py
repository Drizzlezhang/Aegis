"""Agent state and sub-models for pipeline composition."""

from datetime import date, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from pydantic import BaseModel, Field

from .analysis import GEXWall, SupportResistanceLevel, ValuationRange, VolumeProfile
from .market import MarketIndex, OHLCV
from .options import OptionChain

if TYPE_CHECKING:
    from .trade import RecommendedOption


class QuantResult(BaseModel):
    """QuantBrain output container."""

    valuation_range: ValuationRange | None = None
    support_levels: list[SupportResistanceLevel] = Field(default_factory=list)
    resistance_levels: list[SupportResistanceLevel] = Field(default_factory=list)
    volume_profile: VolumeProfile | None = None
    gex_walls: list[GEXWall] = Field(default_factory=list)
    analysis_report: str = ""


class StrategyResult(BaseModel):
    """StrategyExec output container."""

    recommended_options: list["RecommendedOption"] = Field(default_factory=list)
    action_report: str = ""


class AgentState(BaseModel):
    """Main pipeline state with backward-compatible top-level fields."""

    symbol: str
    trade_date: date

    pipeline_id: str = Field(default_factory=lambda: str(uuid4()))
    current_step: int = 0
    total_steps: int = 4

    ohlcv_data: list[OHLCV] | None = None
    options_chain: OptionChain | None = None
    market_indices: list[MarketIndex] = Field(default_factory=list)
    youtube_signals: list[dict[str, Any]] = Field(default_factory=list)

    valuation_range: ValuationRange | None = None
    support_levels: list[SupportResistanceLevel] = Field(default_factory=list)
    resistance_levels: list[SupportResistanceLevel] = Field(default_factory=list)
    volume_profile: VolumeProfile | None = None
    gex_walls: list[GEXWall] = Field(default_factory=list)

    recommended_options: list["RecommendedOption"] = Field(default_factory=list)
    action_report: str = ""
    analysis_report: str = ""

    quant_result: QuantResult = Field(default_factory=QuantResult)
    strategy_result: StrategyResult = Field(default_factory=StrategyResult)

    timestamp: datetime = Field(default_factory=datetime.now)
    agent_sequence: list[str] = Field(default_factory=list)

    def add_agent_step(self, agent_name: str) -> None:
        self.agent_sequence.append(agent_name)

    def snapshot_quant(self) -> QuantResult:
        return QuantResult(
            valuation_range=self.valuation_range,
            support_levels=self.support_levels.copy(),
            resistance_levels=self.resistance_levels.copy(),
            volume_profile=self.volume_profile,
            gex_walls=self.gex_walls.copy(),
            analysis_report=self.analysis_report,
        )

    def snapshot_strategy(self) -> StrategyResult:
        return StrategyResult(
            recommended_options=self.recommended_options.copy(),
            action_report=self.action_report,
        )

    def get_support_prices(self) -> list[float]:
        return sorted(level.price for level in self.support_levels)

    def get_resistance_prices(self) -> list[float]:
        return sorted(level.price for level in self.resistance_levels)


from .trade import RecommendedOption

StrategyResult.model_rebuild()
AgentState.model_rebuild()

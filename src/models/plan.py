"""Trade planning models."""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class StrategyMode(StrEnum):
    LEFT_SIDE = "left_side"
    RIGHT_SIDE = "right_side"


class EntryCondition(BaseModel):
    factor: str
    description: str
    met: bool = False
    weight: float = 1.0


class EntryTranche(BaseModel):
    tranche_number: int
    percentage: float
    trigger: str
    executed: bool = False
    executed_price: float | None = None
    executed_date: date | None = None


class ContractCriteria(BaseModel):
    min_dte: int = 300
    delta_range: tuple[float, float] = (0.6, 0.8)
    max_iv_rank: float = 50.0
    min_open_interest: int = 100
    max_bid_ask_spread_pct: float = 5.0


class StopLoss(BaseModel):
    type: str = "percentage"
    value: float = 50.0
    description: str = "Exit if option loses 50% of entry value"


class ProfitTarget(BaseModel):
    level: int
    percentage: float
    action: str
    description: str


class RollTrigger(BaseModel):
    min_dte_remaining: int = 90
    min_profit_pct: float = 50.0
    roll_to_dte: int = 365
    description: str = "Roll when DTE < 90 and profit > 50%"


class TradePlan(BaseModel):
    strategy_mode: StrategyMode
    contract_criteria: ContractCriteria = Field(default_factory=ContractCriteria)
    entry_conditions: list[EntryCondition] = Field(default_factory=list)
    entry_tranches: list[EntryTranche] = Field(default_factory=list)
    stop_loss: StopLoss = Field(default_factory=StopLoss)
    profit_targets: list[ProfitTarget] = Field(default_factory=list)
    roll_trigger: RollTrigger | None = None
    notes: str = ""

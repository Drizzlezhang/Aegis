"""Advanced options analytics models."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class WallType(StrEnum):
    CALL_WALL = "call_wall"
    PUT_WALL = "put_wall"
    GAMMA_WALL = "gamma_wall"


class CallPutWall(BaseModel):
    strike: float
    wall_type: WallType
    net_gex: float
    call_oi: int = 0
    put_oi: int = 0


class MaxPain(BaseModel):
    strike: float
    total_pain: float
    timestamp: datetime


class IVAnalysis(BaseModel):
    current_iv: float
    iv_rank: float
    iv_percentile: float
    hv_20: float | None = None
    hv_60: float | None = None
    iv_hv_ratio: float | None = None

    @property
    def iv_is_cheap(self) -> bool:
        return self.iv_rank < 30

    @property
    def iv_is_expensive(self) -> bool:
        return self.iv_rank > 70


class FlowDirection(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class UnusualContract(BaseModel):
    symbol: str
    strike: float
    expiry: str
    option_type: str
    volume: int
    open_interest: int
    vol_oi_ratio: float
    premium: float
    direction: FlowDirection


class LargeTrade(BaseModel):
    symbol: str
    strike: float
    expiry: str
    option_type: str
    size: int
    price: float
    premium: float
    side: str
    timestamp: datetime


class OrderFlow(BaseModel):
    unusual_contracts: list[UnusualContract] = Field(default_factory=list)
    large_trades: list[LargeTrade] = Field(default_factory=list)
    call_volume: int = 0
    put_volume: int = 0

    @property
    def net_premium(self) -> float:
        bullish = sum(trade.premium for trade in self.large_trades if trade.side == "buy")
        bearish = sum(trade.premium for trade in self.large_trades if trade.side == "sell")
        return bullish - bearish

    @property
    def put_call_ratio(self) -> float:
        if self.call_volume == 0:
            return float("inf")
        return self.put_volume / self.call_volume


class OptionsAnalytics(BaseModel):
    iv_analysis: IVAnalysis | None = None
    order_flow: OrderFlow | None = None
    max_pain: MaxPain | None = None
    gex_walls: list[CallPutWall] = Field(default_factory=list)

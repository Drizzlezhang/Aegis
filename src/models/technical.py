"""Technical indicator models."""

from pydantic import BaseModel, Field


class TrendIndicators(BaseModel):
    sma_20: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    ema_9: float | None = None
    ema_21: float | None = None
    golden_cross: bool = False
    death_cross: bool = False


class MomentumIndicators(BaseModel):
    rsi_14: float | None = None
    macd_line: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    stoch_k: float | None = None
    stoch_d: float | None = None
    adx: float | None = None


class VolumeIndicators(BaseModel):
    obv: float | None = None
    vwap: float | None = None
    volume_sma_20: float | None = None
    relative_volume: float | None = None


class TechnicalIndicators(BaseModel):
    trend: TrendIndicators = Field(default_factory=TrendIndicators)
    momentum: MomentumIndicators = Field(default_factory=MomentumIndicators)
    volume: VolumeIndicators = Field(default_factory=VolumeIndicators)

    @property
    def is_uptrend(self) -> bool:
        if self.trend.sma_50 is not None and self.trend.sma_200 is not None:
            return self.trend.sma_50 > self.trend.sma_200
        return False

    @property
    def is_oversold(self) -> bool:
        if self.momentum.rsi_14 is not None:
            return self.momentum.rsi_14 < 30
        return False

    @property
    def is_overbought(self) -> bool:
        if self.momentum.rsi_14 is not None:
            return self.momentum.rsi_14 > 70
        return False

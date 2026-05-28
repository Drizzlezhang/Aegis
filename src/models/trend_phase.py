"""Trend phase (Wyckoff cycle) models."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class WyckoffPhase(StrEnum):
    """Wyckoff 6-phase market cycle."""

    ACCUMULATION = "accumulation"
    MARKUP = "markup"
    DISTRIBUTION = "distribution"
    MARKDOWN = "markdown"
    RE_ACCUMULATION = "re_accumulation"
    RE_DISTRIBUTION = "re_distribution"


class DimensionScore(BaseModel):
    """Single dimension scoring result."""

    name: str
    raw_value: float = Field(description="Raw computed value")
    normalized_score: float = Field(ge=0, le=100, description="Normalized 0-100 score")
    weight: float = Field(ge=0, le=1)
    weighted_score: float = Field(ge=0, le=100)


class TrendPhaseResult(BaseModel):
    """Phase Predictor full output."""

    phase: WyckoffPhase
    confidence: float = Field(default=50.0, ge=0, le=100, description="Phase prediction confidence based on dimension agreement")
    composite_score: float = Field(ge=0, le=100, description="Composite score: >60 bullish, <40 bearish")
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    low_volatility_override: bool = Field(default=False, description="ATR/close < threshold triggers neutral override")
    phase_description: str = ""
    transition: str | None = Field(default=None, description="Phase transition signal, e.g. 'accumulation→markup'")
    adx_proxy_used: bool = Field(default=False, description="True when ADX was estimated via proxy (insufficient data for Wilder's ADX)")
    degraded_dimensions: list[str] = Field(default_factory=list, description="Dimension names that failed and were replaced with neutral scores")


class PhaseHistoryRecord(BaseModel):
    """Single phase prediction history entry."""

    id: str | None = None  # UUID, assigned by DB
    symbol: str
    timestamp: datetime
    phase: str  # WyckoffPhase value
    composite_score: float
    confidence: float


class PhaseTrendSummary(BaseModel):
    """Summary of recent phase trend."""

    dominant_phase: str
    transition_count: int
    stability_score: float  # 0-1

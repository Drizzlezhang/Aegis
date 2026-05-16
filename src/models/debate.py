"""辩论系统模型。"""

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field


class DebateRole(StrEnum):
    BULL = "bull"
    BEAR = "bear"
    JUDGE = "judge"
    AGGRESSIVE = "aggressive"
    CONSERVATIVE = "conservative"
    NEUTRAL_ANALYST = "neutral_analyst"
    PORTFOLIO_MANAGER = "portfolio_manager"


class InvestmentRating(StrEnum):
    """5 级投资评级。"""

    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class DebateArgument(BaseModel):
    """单方辩论论点。"""

    role: DebateRole
    position: str  # "bullish" | "bearish" | "neutral"
    key_points: list[str]
    confidence: float = Field(0.5, ge=0, le=1)
    evidence: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class DebateRound(BaseModel):
    """一轮辩论（Bull vs Bear）。"""

    round_number: int = 1
    bull_argument: DebateArgument | None = None
    bear_argument: DebateArgument | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class JudgeVerdict(BaseModel):
    """仲裁裁决。"""

    rating: InvestmentRating
    confidence: float = Field(0.5, ge=0, le=1)
    winning_side: str  # "bull" | "bear" | "neutral"
    reasoning: str
    key_factors: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    dissenting_points: list[str] = Field(default_factory=list)


class DebateResult(BaseModel):
    """完整辩论结果。"""

    symbol: str
    debate_type: str  # "investment" | "risk"
    rounds: list[DebateRound] = Field(default_factory=list)
    verdict: JudgeVerdict | None = None
    total_duration_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
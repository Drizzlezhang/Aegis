"""策略决策结构化输出。"""

from enum import StrEnum

from pydantic import BaseModel, Field


class DecisionRating(StrEnum):
    """5 级决策评级。"""

    STRONG_ENTRY = "strong_entry"
    ENTRY = "entry"
    WATCH = "watch"
    REDUCE = "reduce"
    EXIT = "exit"


class StrategyDecision(BaseModel):
    """策略执行的最终结构化决策。"""

    symbol: str
    rating: DecisionRating
    strategy_mode: str  # "left_side" | "right_side" | "none"
    confidence: float = Field(0.5, ge=0, le=1)

    # 评分依据
    technical_grade: str = "F"
    technical_score: float = 0.0
    macro_regime: str = "neutral"

    # 决策理由
    entry_factors_met: int = 0
    entry_factors_total: int = 0
    primary_reason: str = ""
    supporting_factors: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)

    # Anti-whipsaw
    whipsaw_blocked: bool = False
    whipsaw_reason: str = ""
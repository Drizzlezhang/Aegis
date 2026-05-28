"""Phase Evidence — bridge PhasePredictor output to Debate Agent context."""

from dataclasses import dataclass, field

from src.models.trend_phase import TrendPhaseResult, WyckoffPhase

DIMENSION_DESCRIPTIONS: dict[str, str] = {
    "trend_momentum": "趋势动量",
    "velocity": "价格速度",
    "acceleration": "动量加速度",
    "volume": "成交量确认",
    "mean_reversion": "均值回归",
    "macro": "宏观环境",
    "valuation": "估值水平",
}

PHASE_TO_BIAS: dict[WyckoffPhase, str] = {
    WyckoffPhase.ACCUMULATION: "long",
    WyckoffPhase.MARKUP: "long",
    WyckoffPhase.RE_ACCUMULATION: "long",
    WyckoffPhase.DISTRIBUTION: "reduce",
    WyckoffPhase.MARKDOWN: "short",
    WyckoffPhase.RE_DISTRIBUTION: "reduce",
}


@dataclass
class PhaseEvidence:
    """Structured evidence derived from PhasePredictor for Debate Agent."""

    phase: WyckoffPhase
    composite_score: float
    confidence: float
    bull_factors: list[str] = field(default_factory=list)
    bear_factors: list[str] = field(default_factory=list)
    transition_signal: str | None = None
    position_bias: str = "neutral"


def generate_phase_evidence(result: TrendPhaseResult) -> PhaseEvidence:
    """Convert TrendPhaseResult into structured debate evidence.

    Args:
        result: TrendPhaseResult from PhasePredictor.predict().

    Returns:
        PhaseEvidence with bull/bear factors, position bias, and transition signal.
    """
    bull_factors: list[str] = []
    bear_factors: list[str] = []

    for dim in result.dimension_scores:
        cn_name = DIMENSION_DESCRIPTIONS.get(dim.name, dim.name)
        if dim.normalized_score > 60:
            bull_factors.append(f"{cn_name}强劲({dim.normalized_score:.0f}/100)")
        elif dim.normalized_score < 40:
            bear_factors.append(f"{cn_name}偏弱({dim.normalized_score:.0f}/100)")

    position_bias = PHASE_TO_BIAS.get(result.phase, "neutral")

    # Low confidence override
    if result.confidence < 40:
        position_bias = "neutral"

    return PhaseEvidence(
        phase=result.phase,
        composite_score=result.composite_score,
        confidence=result.confidence,
        bull_factors=bull_factors,
        bear_factors=bear_factors,
        transition_signal=result.transition,
        position_bias=position_bias,
    )

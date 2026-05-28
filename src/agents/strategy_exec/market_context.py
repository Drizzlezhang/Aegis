"""Market context integration for Strategy-Execution Agent."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.models import MarketIndex

if TYPE_CHECKING:
    from src.agents.debate.phase_evidence import PhaseEvidence


@dataclass
class StrategyMarketContext:
    """Market context specifically for strategy decisions."""

    vix_level: float | None = None
    spx_change_pct: float | None = None
    ndx_change_pct: float | None = None
    market_sentiment: str = "neutral"
    volatility_regime: str = "normal"
    # Strategy-specific adjustments
    leaps_call_enabled: bool = True
    leaps_confidence_delta: float = 0.0
    bull_spread_confidence_delta: float = 0.0
    covered_call_confidence_delta: float = 0.0
    position_size_factor: float = 1.0
    risk_warning: str = ""
    tech_caution: bool = False


def analyze_strategy_market_context(market_indices: list[MarketIndex]) -> StrategyMarketContext:
    """Analyze market indices and return strategy-specific context."""
    ctx = StrategyMarketContext()

    # Extract values
    for idx in market_indices:
        sym = idx.symbol.upper()
        if sym in ("^VIX", "VIX"):
            ctx.vix_level = idx.price
        elif sym in ("^GSPC", "SPX"):
            ctx.spx_change_pct = idx.change_percent
        elif sym in ("^IXIC", "NDX"):
            ctx.ndx_change_pct = idx.change_percent

    # Volatility regime and strategy adjustments
    if ctx.vix_level is not None:
        if ctx.vix_level < 15:
            ctx.volatility_regime = "low"
            ctx.leaps_confidence_delta = 0.05
            ctx.covered_call_confidence_delta = -0.05  # Low IV = lower premiums
        elif ctx.vix_level < 25:
            ctx.volatility_regime = "normal"
            # No adjustments in normal regime
        elif ctx.vix_level < 30:
            ctx.volatility_regime = "elevated"
            ctx.leaps_confidence_delta = -0.15
            ctx.bull_spread_confidence_delta = 0.1
            ctx.position_size_factor = 0.8
            ctx.risk_warning = "VIX elevated — reduce position size, prefer defined-risk strategies"
        else:
            ctx.volatility_regime = "high"
            ctx.leaps_call_enabled = False  # Too risky when VIX > 30
            ctx.leaps_confidence_delta = -0.3
            ctx.bull_spread_confidence_delta = 0.15
            ctx.covered_call_confidence_delta = 0.1
            ctx.position_size_factor = 0.5
            ctx.risk_warning = "VIX high (>30) — avoid directional long strategies, favor defined risk"

    # Sentiment adjustments
    spx = ctx.spx_change_pct
    ndx = ctx.ndx_change_pct

    if spx is not None and ndx is not None:
        avg = (spx + ndx) / 2
        if avg > 1.0:
            ctx.market_sentiment = "bullish"
            ctx.leaps_confidence_delta += 0.05
        elif avg < -1.0:
            ctx.market_sentiment = "bearish"
            ctx.leaps_confidence_delta -= 0.1
            ctx.covered_call_confidence_delta += 0.1
    elif spx is not None:
        if spx > 1.0:
            ctx.market_sentiment = "bullish"
            ctx.leaps_confidence_delta += 0.05
        elif spx < -1.0:
            ctx.market_sentiment = "bearish"
            ctx.leaps_confidence_delta -= 0.1
            ctx.covered_call_confidence_delta += 0.1

    # Tech caution
    if ndx is not None and ndx < -2.0:
        ctx.tech_caution = True
        ctx.leaps_confidence_delta -= 0.1
        if not ctx.risk_warning:
            ctx.risk_warning = "NDX down >2% — exercise caution with tech exposure"

    return ctx


def should_skip_leaps_for_tech(
    symbol: str, ctx: StrategyMarketContext
) -> bool:
    """Check if LEAPS should be skipped for tech stocks during tech weakness."""
    tech_symbols = {"QQQ", "NVDA", "AAPL", "MSFT", "PLTR", "NFLX", "TSLA", "INTC", "TSM"}
    return ctx.tech_caution and symbol.upper() in tech_symbols


def format_strategy_market_summary(ctx: StrategyMarketContext) -> str:
    """Format market context for strategy report."""
    lines = ["MACRO MARKET CONTEXT", "-" * 20]

    if ctx.vix_level is not None:
        lines.append(f"VIX: {ctx.vix_level:.2f} ({ctx.volatility_regime})")
    if ctx.spx_change_pct is not None:
        lines.append(f"SPX: {ctx.spx_change_pct:+.2f}%")
    if ctx.ndx_change_pct is not None:
        lines.append(f"NDX: {ctx.ndx_change_pct:+.2f}%")

    lines.append(f"Sentiment: {ctx.market_sentiment}")
    lines.append(f"Position Sizing: {ctx.position_size_factor:.0%}")

    lines.append("\nSTRATEGY ADJUSTMENTS:")
    if not ctx.leaps_call_enabled:
        lines.append("  • LEAPS Call: DISABLED (VIX too high)")
    else:
        delta = ctx.leaps_confidence_delta
        sign = "+" if delta >= 0 else ""
        lines.append(f"  • LEAPS Call: {sign}{delta:.0%} confidence")

    bs_delta = ctx.bull_spread_confidence_delta
    bs_sign = "+" if bs_delta >= 0 else ""
    lines.append(f"  • Bull Spread: {bs_sign}{bs_delta:.0%} confidence")

    cc_delta = ctx.covered_call_confidence_delta
    cc_sign = "+" if cc_delta >= 0 else ""
    lines.append(f"  • Covered Call: {cc_sign}{cc_delta:.0%} confidence")

    if ctx.tech_caution:
        lines.append("  • Tech stocks: extra caution applied")

    if ctx.risk_warning:
        lines.append(f"\nWARNING: {ctx.risk_warning}")

    return "\n".join(lines)


def adjust_position_for_phase(
    base_position_size: float,
    phase_evidence: "PhaseEvidence | None",
) -> float:
    """Adjust position size based on Wyckoff phase signal.

    Args:
        base_position_size: Original position size from strategy.
        phase_evidence: PhaseEvidence from PhasePredictor, or None.

    Returns:
        Adjusted position size.
    """
    if phase_evidence is None:
        return base_position_size

    multipliers = {
        "long": 1.2,
        "reduce": 0.5,
        "short": 0.3,
        "neutral": 0.8,
    }
    multiplier = multipliers.get(phase_evidence.position_bias, 1.0)

    # Confidence modulation: low confidence → multiplier closer to 1.0
    confidence_mod = phase_evidence.confidence / 100.0
    adjusted_multiplier = 1.0 + (multiplier - 1.0) * confidence_mod

    return base_position_size * adjusted_multiplier

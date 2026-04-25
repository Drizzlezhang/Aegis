"""Market context analysis for Quant-Brain Agent."""

from dataclasses import dataclass

from src.models import MarketIndex


@dataclass
class MarketContext:
    """Computed market context for adjusting analysis."""

    vix_level: float | None = None
    spx_change_pct: float | None = None
    ndx_change_pct: float | None = None
    market_sentiment: str = "neutral"  # "bullish", "bearish", "neutral"
    volatility_regime: str = "normal"  # "low", "normal", "elevated", "high"
    confidence_adjustment: float = 0.0
    position_size_factor: float = 1.0
    risk_warning: str = ""


def analyze_market_context(market_indices: list[MarketIndex]) -> MarketContext:
    """Analyze market indices and return computed market context."""
    ctx = MarketContext()

    # Extract values from market indices
    for idx in market_indices:
        sym = idx.symbol.upper()
        if sym in ("^VIX", "VIX"):
            ctx.vix_level = idx.price
        elif sym in ("^GSPC", "SPX"):
            ctx.spx_change_pct = idx.change_percent
        elif sym in ("^IXIC", "NDX"):
            ctx.ndx_change_pct = idx.change_percent

    # Determine volatility regime from VIX
    if ctx.vix_level is not None:
        if ctx.vix_level < 15:
            ctx.volatility_regime = "low"
            ctx.confidence_adjustment = 0.05
        elif ctx.vix_level < 25:
            ctx.volatility_regime = "normal"
            ctx.confidence_adjustment = 0.0
        elif ctx.vix_level < 30:
            ctx.volatility_regime = "elevated"
            ctx.confidence_adjustment = -0.08
            ctx.position_size_factor = 0.8
            ctx.risk_warning = "VIX elevated — reduce position size"
        else:
            ctx.volatility_regime = "high"
            ctx.confidence_adjustment = -0.15
            ctx.position_size_factor = 0.5
            ctx.risk_warning = "VIX high (>30) — significant risk-off, avoid new positions"

    # Determine market sentiment from SPX and NDX
    spx = ctx.spx_change_pct
    ndx = ctx.ndx_change_pct

    if spx is not None and ndx is not None:
        avg_change = (spx + ndx) / 2
        if avg_change > 1.0:
            ctx.market_sentiment = "bullish"
        elif avg_change < -1.0:
            ctx.market_sentiment = "bearish"
        else:
            ctx.market_sentiment = "neutral"
    elif spx is not None:
        if spx > 1.0:
            ctx.market_sentiment = "bullish"
        elif spx < -1.0:
            ctx.market_sentiment = "bearish"
        else:
            ctx.market_sentiment = "neutral"
    elif ndx is not None:
        if ndx > 1.5:
            ctx.market_sentiment = "bullish"
        elif ndx < -1.5:
            ctx.market_sentiment = "bearish"
        else:
            ctx.market_sentiment = "neutral"

    # Extra penalty for tech stocks when NDX drops sharply
    if ndx is not None and ndx < -2.0 and ctx.confidence_adjustment > -0.15:
        ctx.confidence_adjustment = max(ctx.confidence_adjustment - 0.05, -0.15)
        if not ctx.risk_warning:
            ctx.risk_warning = "NDX down >2% — tech weakness, exercise caution"

    return ctx


def adjust_confidence_for_market(
    base_confidence: float,
    level_type: str,
    market_context: MarketContext | None,
) -> float:
    """Adjust support/resistance confidence based on market context."""
    if market_context is None:
        return base_confidence

    adjusted = base_confidence + market_context.confidence_adjustment

    # Sentiment-driven fine-tuning
    if market_context.market_sentiment == "bullish" and level_type == "support":
        adjusted += 0.03
    elif market_context.market_sentiment == "bearish" and level_type == "resistance":
        adjusted += 0.03
    elif market_context.market_sentiment == "bearish" and level_type == "support":
        adjusted -= 0.03
    elif market_context.market_sentiment == "bullish" and level_type == "resistance":
        adjusted -= 0.03

    # Clamp to valid range
    return max(0.1, min(0.99, adjusted))


def format_market_summary(market_context: MarketContext) -> str:
    """Format market context as a string for reports or LLM prompts."""
    lines = ["MARKET CONTEXT", "-" * 20]

    if market_context.vix_level is not None:
        lines.append(f"VIX: {market_context.vix_level:.2f} ({market_context.volatility_regime})")
    if market_context.spx_change_pct is not None:
        lines.append(f"SPX Change: {market_context.spx_change_pct:+.2f}%")
    if market_context.ndx_change_pct is not None:
        lines.append(f"NDX Change: {market_context.ndx_change_pct:+.2f}%")

    lines.append(f"Market Sentiment: {market_context.market_sentiment}")
    lines.append(f"Position Size Factor: {market_context.position_size_factor:.0%}")

    if market_context.risk_warning:
        lines.append(f"Risk Warning: {market_context.risk_warning}")

    return "\n".join(lines)

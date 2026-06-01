"""Enhanced LLM integration for Quant-Brain Agent."""

import logging
from typing import Any

from src.llm import generate
from src.models import AgentState, GEXWall, SupportResistanceLevel, ValuationRange, VolumeProfile

from .llm_guard import llm_optional
from .market_context import MarketContext, format_market_summary

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_ANALYST = """你是 Aegis-Trader 的量化分析师。基于提供的技术指标数据，生成简洁的投资分析段落。

规则：
1. 只基于数据说话，不编造数字
2. 明确指出看多/看空信号及其强度
3. 给出具体价位参考（支撑/阻力/入场区间）
4. 风险提示必须具体，不泛泛而谈
5. 中文输出，专业术语保留英文缩写
6. 总长度 300-500 字"""


@llm_optional(fallback_value="")
async def generate_llm_enhanced_report(
    symbol: str,
    ohlcv_data: list[Any] | None = None,
    options_chain: Any | None = None,
    support_levels: list[SupportResistanceLevel] | None = None,
    resistance_levels: list[SupportResistanceLevel] | None = None,
    volume_profile: VolumeProfile | None = None,
    gex_walls: list[GEXWall] | None = None,
    valuation_range: ValuationRange | None = None,
    market_context: MarketContext | None = None,
    technical_summary: dict | None = None,
) -> str:
    """
    Generate enhanced analysis report using LLM.

    Args:
        symbol: Stock symbol
        ohlcv_data: OHLCV data
        options_chain: Options chain data
        support_levels: Support levels
        resistance_levels: Resistance levels
        volume_profile: Volume profile data
        gex_walls: GEX walls
        valuation_range: Valuation range
        market_context: Computed market context for macro adjustment

    Returns:
        Enhanced analysis report
    """
    if technical_summary is None and isinstance(ohlcv_data, dict):
        technical_summary = ohlcv_data
        if support_levels is None and isinstance(options_chain, list):
            support_levels = options_chain
        if valuation_range is None and not isinstance(resistance_levels, list):
            valuation_range = resistance_levels
        if market_context is None and volume_profile is not None:
            market_context = volume_profile

    if technical_summary is not None:
        prompt = _build_analysis_prompt(symbol, technical_summary, support_levels or [], valuation_range, market_context)
        report = await generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT_ANALYST,
            max_tokens=1500,
            temperature=0.3,
        )
        return report or ""

    # Create data summary for LLM
    data_summary = _create_data_summary(
        symbol=symbol,
        ohlcv_data=ohlcv_data,
        options_chain=options_chain,
        support_levels=support_levels,
        resistance_levels=resistance_levels,
        volume_profile=volume_profile,
        gex_walls=gex_walls,
        valuation_range=valuation_range,
        market_context=market_context,
    )

    # Build macro context paragraph
    macro_paragraph = ""
    if market_context:
        macro_paragraph = (
            f"\nMACRO MARKET CONTEXT:\n"
            f"- Volatility Regime (VIX): {market_context.volatility_regime}\n"
            f"- Market Sentiment: {market_context.market_sentiment}\n"
            f"- Recommended Position Size Factor: {market_context.position_size_factor:.0%}\n"
        )
        if market_context.risk_warning:
            macro_paragraph += f"- Risk Warning: {market_context.risk_warning}\n"

    # Generate enhanced report using LLM
    report: str = await generate(
        prompt=f"""You are a senior quantitative analyst. Analyze this market data and provide a professional trading analysis report.

Data Summary:
{data_summary}{macro_paragraph}

Please provide a comprehensive analysis including:

1. EXECUTIVE SUMMARY
   - Key market observations
   - Overall trend assessment
   - Risk level assessment

2. TECHNICAL ANALYSIS
   - Support and resistance levels analysis
   - Volume profile insights
   - GEX wall implications for price action


3. VALUATION ASSESSMENT
   - Current valuation relative to fair value
   - PE-band positioning
   - Investment attractiveness


4. OPTIONS STRATEGY INSIGHTS
   - Suitable options strategies based on analysis
   - Risk-reward considerations
   - Entry and exit considerations


5. RISK MANAGEMENT RECOMMENDATIONS
   - Position sizing suggestions (respect the position size factor from macro context)
   - Stop-loss placement
   - Portfolio allocation considerations


IMPORTANT: Incorporate the macro market context (VIX level, market sentiment, position size factor) into your analysis. When VIX is elevated or market sentiment is bearish, be more conservative with recommendations.""",
        system_prompt="""You are a senior quantitative analyst at a hedge fund specializing in options trading and market analysis.
You have deep expertise in technical analysis, options pricing, and risk management.
Provide professional, data-driven insights suitable for institutional investors.
Always factor in the macro market context (VIX, SPX/NDX trend) when making recommendations.""",
        max_tokens=4000,
        temperature=0.3,
    )

    logger.info(f"Generated enhanced LLM report for {symbol}")
    return report or ""


def _build_analysis_prompt(
    symbol: str,
    technical: dict,
    supports: list[Any],
    valuation: Any | None,
    macro: Any | None,
) -> str:
    parts = [f"标的: {symbol}"]
    parts.append(f"技术评分: {technical.get('score', 'N/A')}/100, Grade: {technical.get('grade', 'N/A')}")
    parts.append(f"趋势: {technical.get('trend', 'N/A')}")
    if technical.get("signals"):
        parts.append(f"信号: {', '.join(technical['signals'])}")
    if supports:
        parts.append(f"支撑位: {supports}")
    if valuation:
        parts.append(f"估值区间: {valuation}")
    if macro:
        parts.append(f"宏观环境: {macro}")
    return "\n".join(parts)


def _create_data_summary(
    symbol: str,
    ohlcv_data: list[Any] | None = None,
    options_chain: Any | None = None,
    support_levels: list[SupportResistanceLevel] | None = None,
    resistance_levels: list[SupportResistanceLevel] | None = None,
    volume_profile: VolumeProfile | None = None,
    gex_walls: list[GEXWall] | None = None,
    valuation_range: ValuationRange | None = None,
    market_context: MarketContext | None = None,
) -> str:
    """Create a structured data summary for LLM analysis."""
    summary = f"ANALYSIS DATA FOR {symbol}\n"
    summary += "=" * 50 + "\n\n"

    # Market Context
    if market_context:
        summary += format_market_summary(market_context) + "\n\n"

    # Market Data
    summary += "MARKET DATA\n"
    summary += "-" * 20 + "\n"
    if ohlcv_data and len(ohlcv_data) > 0:
        latest = ohlcv_data[-1]
        summary += f"Latest OHLCV: {latest.timestamp.date()} O={latest.open:.2f} H={latest.high:.2f} L={latest.low:.2f} C={latest.close:.2f} V={latest.volume:,}\n"
        summary += f"Data Points: {len(ohlcv_data)} days\n"
    else:
        summary += "No OHLCV data available\n"

    # Options Data
    if options_chain:
        summary += "\nOPTIONS CHAIN\n"
        summary += "-" * 20 + "\n"
        summary += f"Spot Price: {options_chain.spot_price:.2f}\n"
        summary += f"Calls: {len(options_chain.calls)} contracts\n"
        summary += f"Puts: {len(options_chain.puts)} contracts\n"
        summary += f"Expiry Dates: {len(options_chain.expiry_dates)}\n"

    # Support Levels
    if support_levels:
        summary += "\nSUPPORT LEVELS (Top 5 by confidence)\n"
        summary += "-" * 20 + "\n"
        for i, level in enumerate(sorted(support_levels, key=lambda x: x.confidence, reverse=True)[:5], 1):
            summary += f"{i}. {level.price:.2f} ({level.source}, confidence: {level.confidence:.1%})\n"

    # Resistance Levels
    if resistance_levels:
        summary += "\nRESISTANCE LEVELS (Top 5 by confidence)\n"
        summary += "-" * 20 + "\n"
        for i, level in enumerate(sorted(resistance_levels, key=lambda x: x.confidence, reverse=True)[:5], 1):
            summary += f"{i}. {level.price:.2f} ({level.source}, confidence: {level.confidence:.1%})\n"

    # Volume Profile
    if volume_profile:
        summary += "\nVOLUME PROFILE\n"
        summary += "-" * 20 + "\n"
        summary += f"POC (Point of Control): {volume_profile.poc_price:.2f}\n"
        summary += f"VAH (Value Area High): {volume_profile.vah_price:.2f}\n"
        summary += f"VAL (Value Area Low): {volume_profile.val_price:.2f}\n"
        summary += f"Value Area Range: {volume_profile.value_area_range:.2f}\n"
        summary += f"POC Volume %: {volume_profile.poc_percentage:.1f}%\n"

    # GEX Walls
    if gex_walls:
        support_walls = [w for w in gex_walls if w.is_support]
        resistance_walls = [w for w in gex_walls if w.is_resistance]

        summary += "\nGEX WALLS\n"
        summary += "-" * 20 + "\n"
        summary += f"Support Walls: {len(support_walls)}\n"
        if support_walls:
            strongest = max(support_walls, key=lambda w: w.absolute_gex)
            summary += f"Strongest Support: {strongest.strike:.2f} (GEX: {strongest.net_gex:,.0f})\n"

        summary += f"Resistance Walls: {len(resistance_walls)}\n"
        if resistance_walls:
            strongest = max(resistance_walls, key=lambda w: w.absolute_gex)
            summary += f"Strongest Resistance: {strongest.strike:.2f} (GEX: {strongest.net_gex:,.0f})\n"

    # Valuation
    if valuation_range:
        summary += "\nVALUATION (PE-Band)\n"
        summary += "-" * 20 + "\n"
        summary += f"Current Price: {valuation_range.current_price:.2f}\n"
        summary += f"Fair Estimate: {valuation_range.fair_estimate:.2f}\n"
        summary += f"Discount to Fair: {valuation_range.discount_to_fair:.1f}%\n"
        summary += f"Status: {'UNDERVALUED' if valuation_range.is_undervalued else 'OVERVALUED' if valuation_range.is_overvalued else 'FAIR VALUE'}\n"
        if valuation_range.pe_percentile:
            summary += f"PE Percentile: {valuation_range.pe_percentile:.1f}%\n"

    return summary


def _create_basic_report(data_summary: str) -> str:
    """Create a basic report when LLM fails."""
    report = "BASIC ANALYSIS REPORT\n"
    report += "=" * 50 + "\n\n"
    report += "Note: LLM enhancement unavailable. Using basic data summary.\n\n"
    report += data_summary
    report += "\n\nRECOMMENDATION: Review the data above and consult with a financial advisor.\n"
    return report


# Example usage in Quant-Brain Agent
async def integrate_llm_into_quant_brain(agent_instance: Any, state: AgentState) -> None:
    """
    Example integration function for Quant-Brain Agent.

    Usage in Quant-Brain Agent's run() method:
    ```
    # After calculations, generate enhanced report
    from src.agents.quant_brain.llm_integration import generate_llm_enhanced_report

    enhanced_report = await generate_llm_enhanced_report(
        symbol=state.symbol,
        ohlcv_data=state.ohlcv_data,
        options_chain=state.options_chain,
        support_levels=state.support_levels,
        resistance_levels=state.resistance_levels,
        volume_profile=state.volume_profile,
        gex_walls=state.gex_walls,
        valuation_range=state.valuation_range
    )

    # Add to state or use as needed
    state.analysis_report = enhanced_report
    ```
    """
    # This function demonstrates how to integrate LLM into existing agent
    # The actual implementation would be in the agent's run() method
    pass

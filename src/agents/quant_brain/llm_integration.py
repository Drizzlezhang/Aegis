"""Enhanced LLM integration for Quant-Brain Agent."""

from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

from src.llm import generate, TaskType
from src.models import SupportResistanceLevel, VolumeProfile, GEXWall, ValuationRange


logger = logging.getLogger(__name__)


async def generate_llm_enhanced_report(
    symbol: str,
    ohlcv_data: Optional[List[Any]] = None,
    options_chain: Optional[Any] = None,
    support_levels: Optional[List[SupportResistanceLevel]] = None,
    resistance_levels: Optional[List[SupportResistanceLevel]] = None,
    volume_profile: Optional[VolumeProfile] = None,
    gex_walls: Optional[List[GEXWall]] = None,
    valuation_range: Optional[ValuationRange] = None
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

    Returns:
        Enhanced analysis report
    """
    # Create data summary for LLM
    data_summary = _create_data_summary(
        symbol=symbol,
        ohlcv_data=ohlcv_data,
        options_chain=options_chain,
        support_levels=support_levels,
        resistance_levels=resistance_levels,
        volume_profile=volume_profile,
        gex_walls=gex_walls,
        valuation_range=valuation_range
    )

    try:
        # Generate enhanced report using LLM
        report = await generate(
            prompt=f"""You are a senior quantitative analyst. Analyze this market data and provide a professional trading analysis report.

Data Summary:
{data_summary}

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
   - Position sizing suggestions
   - Stop-loss placement
   - Portfolio allocation considerations


Format the report professionally with clear sections, bullet points for key points, and actionable recommendations.""",
            system_prompt="""You are a senior quantitative analyst at a hedge fund specializing in options trading and market analysis.
You have deep expertise in technical analysis, options pricing, and risk management.
Provide professional, data-driven insights suitable for institutional investors.""",
            task_type=TaskType.ANALYSIS,
            max_tokens=4000,
            temperature=0.3
        )

        logger.info(f"Generated enhanced LLM report for {symbol}")
        return report

    except Exception as e:
        logger.error(f"LLM report generation failed for {symbol}: {e}")
        # Fallback to basic report
        return _create_basic_report(data_summary)


def _create_data_summary(
    symbol: str,
    ohlcv_data: Optional[List[Any]] = None,
    options_chain: Optional[Any] = None,
    support_levels: Optional[List[SupportResistanceLevel]] = None,
    resistance_levels: Optional[List[SupportResistanceLevel]] = None,
    volume_profile: Optional[VolumeProfile] = None,
    gex_walls: Optional[List[GEXWall]] = None,
    valuation_range: Optional[ValuationRange] = None
) -> str:
    """Create a structured data summary for LLM analysis."""
    summary = f"ANALYSIS DATA FOR {symbol}\n"
    summary += "=" * 50 + "\n\n"

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
        summary += f"\nOPTIONS CHAIN\n"
        summary += "-" * 20 + "\n"
        summary += f"Spot Price: {options_chain.spot_price:.2f}\n"
        summary += f"Calls: {len(options_chain.calls)} contracts\n"
        summary += f"Puts: {len(options_chain.puts)} contracts\n"
        summary += f"Expiry Dates: {len(options_chain.expiry_dates)}\n"

    # Support Levels
    if support_levels:
        summary += f"\nSUPPORT LEVELS (Top 5 by confidence)\n"
        summary += "-" * 20 + "\n"
        for i, level in enumerate(sorted(support_levels, key=lambda x: x.confidence, reverse=True)[:5], 1):
            summary += f"{i}. {level.price:.2f} ({level.source}, confidence: {level.confidence:.1%})\n"

    # Resistance Levels
    if resistance_levels:
        summary += f"\nRESISTANCE LEVELS (Top 5 by confidence)\n"
        summary += "-" * 20 + "\n"
        for i, level in enumerate(sorted(resistance_levels, key=lambda x: x.confidence, reverse=True)[:5], 1):
            summary += f"{i}. {level.price:.2f} ({level.source}, confidence: {level.confidence:.1%})\n"

    # Volume Profile
    if volume_profile:
        summary += f"\nVOLUME PROFILE\n"
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

        summary += f"\nGEX WALLS\n"
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
        summary += f"\nVALUATION (PE-Band)\n"
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
async def integrate_llm_into_quant_brain(agent_instance, state):
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
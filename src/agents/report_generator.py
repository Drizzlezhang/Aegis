"""Report generation for Orchestrator."""

from datetime import UTC, datetime

from src.models import AgentState


def generate_final_report(state: AgentState) -> str:
    """Generate final analysis report from agent state."""
    symbol = state.symbol
    report = f"""
{'=' * 70}
AEGIS-TRADER ANALYSIS REPORT
{'=' * 70}
Symbol: {symbol}
Trade Date: {state.trade_date}
Analysis Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S %Z')}
Pipeline: {' -> '.join(state.agent_sequence)}

{'=' * 70}
1. MARKET DATA SUMMARY
{'=' * 70}
"""

    if state.ohlcv_data:
        latest = state.ohlcv_data[-1] if state.ohlcv_data else None
        if latest:
            report += f"""
Latest Price: {latest.close:.2f}
Volume: {latest.volume:,}
Data Points: {len(state.ohlcv_data)} days
"""
    else:
        report += "\nNo market data available\n"

    if state.options_chain:
        report += f"""
Options Chain:
  Spot Price: {state.options_chain.spot_price:.2f}
  Calls: {len(state.options_chain.calls)} contracts
  Puts: {len(state.options_chain.puts)} contracts
  Expiry Dates: {len(state.options_chain.expiry_dates)}
"""

    report += f"""
{'=' * 70}
2. QUANTITATIVE ANALYSIS
{'=' * 70}
"""

    if state.volume_profile:
        report += f"""
Volume Profile:
  POC (Point of Control): {state.volume_profile.poc_price:.2f}
  VAH (Value Area High): {state.volume_profile.vah_price:.2f}
  VAL (Value Area Low): {state.volume_profile.val_price:.2f}
"""

    if state.gex_walls:
        support_walls = [w for w in state.gex_walls if w.is_support]
        resistance_walls = [w for w in state.gex_walls if w.is_resistance]
        report += f"""
GEX Walls:
  Support Walls: {len(support_walls)}
  Resistance Walls: {len(resistance_walls)}
"""
        if support_walls:
            strongest = max(support_walls, key=lambda w: w.absolute_gex)
            report += f"  Strongest Support: {strongest.strike:.2f} (GEX: {strongest.net_gex:,.0f})\n"

    if state.valuation_range:
        report += f"""
Valuation (PE-Band):
  Current Price: {state.valuation_range.current_price:.2f}
  Fair Estimate: {state.valuation_range.fair_estimate:.2f}
  Discount to Fair: {state.valuation_range.discount_to_fair:.1f}%
  Status: {'UNDervalued' if state.valuation_range.is_undervalued else 'OVERvalued' if state.valuation_range.is_overvalued else 'FAIR'}
"""

    if state.support_levels:
        report += "\nSupport Levels:\n"
        for level in state.support_levels[:5]:
            report += f"  {level.price:.2f} ({level.source}, confidence: {level.confidence:.1%})\n"

    if state.resistance_levels:
        report += "\nResistance Levels:\n"
        for level in state.resistance_levels[:5]:
            report += f"  {level.price:.2f} ({level.source}, confidence: {level.confidence:.1%})\n"

    report += f"""
{'=' * 70}
3. STRATEGY RECOMMENDATIONS
{'=' * 70}
"""

    if state.recommended_options:
        for i, rec in enumerate(state.recommended_options, 1):
            report += f"""
{i}. {rec.recommendation_type.upper().replace('_', ' ')}
   Contract: {rec.contract.contract_symbol}
   Strike: {rec.contract.strike:.2f}, Expiry: {rec.contract.expiry}
   Entry Price: {rec.entry_price:.2f}
   Target Price: {rec.target_price:.2f if rec.target_price else 'N/A'}
   Stop Loss: {rec.stop_loss:.2f if rec.stop_loss else 'N/A'}
   Risk/Reward: {rec.risk_reward_ratio:.2f if rec.risk_reward_ratio else 'N/A'}
   Confidence: {rec.confidence:.1%}

   Reasoning:
   {rec.reasoning}
"""
    else:
        report += "\nNo suitable strategies found for current market conditions.\n"

    report += f"""
{'=' * 70}
4. ACTION REPORT
{'=' * 70}
{state.action_report}

{'=' * 70}
5. RISK DISCLAIMER
{'=' * 70}
⚠️  IMPORTANT RISK WARNINGS:
   • This analysis is for informational purposes only
   • Options trading involves significant risk of loss
   • Past performance does not guarantee future results
   • Always do your own due diligence
   • Consider your risk tolerance and investment objectives
   • Position sizing: Never risk more than 2-5% per trade

{'=' * 70}
END OF REPORT
{'=' * 70}
"""

    return report

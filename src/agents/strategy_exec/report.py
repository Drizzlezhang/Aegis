"""Report generation for Strategy-Execution Agent."""

from typing import Any

from src.models import RecommendedOption, SupportResistanceLevel


def create_action_report(
    symbol: str,
    recommendations: list[RecommendedOption],
    support_levels: list[SupportResistanceLevel],
    resistance_levels: list[SupportResistanceLevel],
    valuation_range: Any | None
) -> str:
    """Create action report with strategy recommendations."""
    report = f"Strategy-Execution Report for {symbol}\n"
    report += "=" * 50 + "\n"

    # Market context
    report += "📊 MARKET CONTEXT\n"
    if support_levels:
        strongest = max(support_levels, key=lambda x: x.confidence)
        report += f"  • Key Support: {strongest.price:.2f} (confidence: {strongest.confidence:.1%})\n"
    if resistance_levels:
        nearest = min(resistance_levels, key=lambda x: x.price)
        report += f"  • Key Resistance: {nearest.price:.2f} (confidence: {nearest.confidence:.1%})\n"
    if valuation_range:
        report += f"  • Valuation: {valuation_range.discount_to_fair:.1f}% discount to fair\n"

    # Recommendations
    report += f"\n🎯 STRATEGY RECOMMENDATIONS ({len(recommendations)} total)\n"

    for i, rec in enumerate(recommendations, 1):
        report += f"\n{i}. {rec.recommendation_type.upper().replace('_', ' ')}\n"
        report += f"   Contract: {rec.contract.contract_symbol}\n"
        report += f"   Strike: {rec.contract.strike:.2f}, Expiry: {rec.contract.expiry}\n"
        report += f"   Entry Price: {rec.entry_price:.2f}\n"
        if rec.target_price:
            report += f"   Target Price: {rec.target_price:.2f}\n"
        if rec.stop_loss:
            report += f"   Stop Loss: {rec.stop_loss:.2f}\n"
        if rec.risk_reward_ratio:
            report += f"   Risk/Reward: {rec.risk_reward_ratio:.2f}\n"
        report += f"   Confidence: {rec.confidence:.1%}\n"
        report += f"   Reasoning: {rec.reasoning}\n"

    if not recommendations:
        report += "\n  No suitable strategies found for current market conditions.\n"
        report += "  Consider waiting for better entry opportunities.\n"

    # Risk warnings
    report += "\n⚠️ RISK WARNINGS\n"
    report += "  • Options trading involves significant risk of loss\n"
    report += "  • LEAPS strategies require long-term capital commitment\n"
    report += "  • Always consider position sizing (max 2-5% per trade)\n"
    report += "  • Monitor VIX and overall market volatility\n"

    report += "=" * 50
    return report

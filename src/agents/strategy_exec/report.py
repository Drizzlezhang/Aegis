"""Report generation for Strategy-Execution Agent."""

from typing import Any

from src.agents.quant_brain.llm_guard import llm_optional
from src.llm import generate
from src.models import RecommendedOption, SupportResistanceLevel

from .market_context import StrategyMarketContext, format_strategy_market_summary

SYSTEM_PROMPT_STRATEGIST = """你是期权策略师。为给定的策略推荐生成简明的中文理由说明（100-200字）。
包含: 选择该 strike/expiry 的逻辑、风险收益比、关键触发条件。"""


@llm_optional(fallback_value="")
async def generate_strategy_reasoning(
    symbol: str,
    recommendation: RecommendedOption,
    support_levels: list[SupportResistanceLevel],
    debate_verdict: dict | None,
) -> str:
    prompt = _build_strategy_prompt(symbol, recommendation, support_levels, debate_verdict)
    response = await generate(
        prompt=prompt,
        system_prompt=SYSTEM_PROMPT_STRATEGIST,
        max_tokens=600,
        temperature=0.3,
    )
    return response or ""


def _build_strategy_prompt(
    symbol: str,
    rec: RecommendedOption,
    supports: list[SupportResistanceLevel],
    debate: dict | None,
) -> str:
    parts = [
        f"标的: {symbol}",
        f"推荐策略: {rec.recommendation_type}",
        f"Strike: {rec.contract.strike}, Expiry: {rec.contract.expiry}",
        f"信心度: {rec.confidence}",
    ]
    if supports:
        parts.append(f"支撑位: {[level.price for level in supports]}")
    if debate:
        parts.append(f"辩论裁决: {debate.get('verdict') or debate.get('rating', 'N/A')}, 信心: {debate.get('confidence', 'N/A')}")
    return "\n".join(parts)


def create_action_report(
    symbol: str,
    recommendations: list[RecommendedOption],
    support_levels: list[SupportResistanceLevel],
    resistance_levels: list[SupportResistanceLevel],
    valuation_range: Any | None,
    market_context: StrategyMarketContext | None = None,
) -> str:
    """Create action report with strategy recommendations."""
    report = f"Strategy-Execution Report for {symbol}\n"
    report += "=" * 50 + "\n"

    # Macro market context
    if market_context:
        report += format_strategy_market_summary(market_context) + "\n\n"

    # Technical context
    report += "📊 TECHNICAL CONTEXT\n"
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
    if market_context and market_context.position_size_factor < 1.0:
        report += f"  • REDUCE POSITION SIZE to {market_context.position_size_factor:.0%} due to elevated risk\n"
    else:
        report += "  • Always consider position sizing (max 2-5% per trade)\n"
    report += "  • Monitor VIX and overall market volatility\n"

    report += "=" * 50
    return report

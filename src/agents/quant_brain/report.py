"""Quant-Brain report generation."""

from typing import Any

from src.models import SupportResistanceLevel, ValuationRange


def create_analysis_report(
    symbol: str,
    volume_profile: Any | None,
    gex_walls: list[Any] | None,
    support_levels: list[SupportResistanceLevel],
    resistance_levels: list[SupportResistanceLevel],
    valuation_range: ValuationRange | None
) -> str:
    """Create quantitative analysis report."""
    report = f"Quant-Brain Analysis Report for {symbol}\n"
    report += "=" * 50 + "\n"

    # Volume Profile summary
    report += "📊 VOLUME PROFILE\n"
    if volume_profile:
        report += f"  • POC: {volume_profile.poc_price:.2f} (Point of Control)\n"
        report += f"  • VAH: {volume_profile.vah_price:.2f} (Value Area High)\n"
        report += f"  • VAL: {volume_profile.val_price:.2f} (Value Area Low)\n"
        report += f"  • Value Area Range: {volume_profile.value_area_range:.2f}\n"
    else:
        report += "  • Not available\n"

    # GEX summary
    report += "\n🛡️ GEX WALLS\n"
    if gex_walls:
        support_walls = [w for w in gex_walls if w.is_support]
        resistance_walls = [w for w in gex_walls if w.is_resistance]

        if support_walls:
            strongest = max(support_walls, key=lambda w: w.absolute_gex)
            report += f"  • Strongest Support: {strongest.strike:.2f} (GEX: {strongest.net_gex:,.0f})\n"
        if resistance_walls:
            strongest = max(resistance_walls, key=lambda w: w.absolute_gex)
            report += f"  • Strongest Resistance: {strongest.strike:.2f} (GEX: {strongest.net_gex:,.0f})\n"
        report += f"  • Total Walls: {len(gex_walls)} (S: {len(support_walls)}, R: {len(resistance_walls)})\n"
    else:
        report += "  • Not available\n"

    # Support/Resistance summary
    report += "\n📈 SUPPORT/RESISTANCE LEVELS\n"
    _append_levels(report, "Support", support_levels)
    _append_levels(report, "Resistance", resistance_levels)

    # Valuation summary
    report += "\n💰 VALUATION RANGE\n"
    _append_valuation(report, valuation_range)

    report += "=" * 50
    return report


def _append_levels(report: str, label: str, levels: list[SupportResistanceLevel]) -> None:
    """Append levels to report."""
    if levels:
        report += f"  • {label} Levels ({len(levels)}):\n"
        for level in levels[:3]:
            report += f"    - {level.price:.2f} ({level.source}, confidence: {level.confidence:.1%})\n"
        if len(levels) > 3:
            report += f"    - ... and {len(levels) - 3} more\n"
    else:
        report += f"  • No {label.lower()} levels identified\n"


def _append_valuation(report: str, valuation_range: ValuationRange | None) -> None:
    """Append valuation to report."""
    if valuation_range:
        report += f"  • Current Price: {valuation_range.current_price:.2f}\n"
        report += f"  • Fair Estimate: {valuation_range.fair_estimate:.2f}\n"
        report += f"  • Low Estimate: {valuation_range.low_estimate:.2f}\n"
        report += f"  • High Estimate: {valuation_range.high_estimate:.2f}\n"
        report += f"  • Discount to Fair: {valuation_range.discount_to_fair:.1f}%\n"
        if valuation_range.is_undervalued:
            report += "  • 📉 UNDERVALUED\n"
        elif valuation_range.is_overvalued:
            report += "  • 📈 OVERVALUED\n"
        else:
            report += "  • ⚖️ FAIRLY VALUED\n"
        if valuation_range.pe_percentile:
            report += f"  • PE Percentile: {valuation_range.pe_percentile:.0%}\n"
    else:
        report += "  • Not available\n"

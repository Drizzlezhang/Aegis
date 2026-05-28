"""Phase description internationalization (i18n).

Hardcoded dict for 6 phases × 2 locales. See ADR-2.
"""

from __future__ import annotations

from src.models.trend_phase import WyckoffPhase

PHASE_DESCRIPTIONS: dict[WyckoffPhase, dict[str, str]] = {
    WyckoffPhase.ACCUMULATION: {
        "en": "Smart money accumulating at range lows",
        "zh-CN": "主力资金在区间低位吸筹",
    },
    WyckoffPhase.MARKUP: {
        "en": "Uptrend in progress with strong momentum",
        "zh-CN": "上升趋势进行中，动能强劲",
    },
    WyckoffPhase.DISTRIBUTION: {
        "en": "Smart money distributing at range highs",
        "zh-CN": "主力资金在区间高位派发",
    },
    WyckoffPhase.MARKDOWN: {
        "en": "Downtrend in progress with selling pressure",
        "zh-CN": "下跌趋势进行中，抛压持续",
    },
    WyckoffPhase.RE_ACCUMULATION: {
        "en": "Pause in uptrend, likely continuation",
        "zh-CN": "上升趋势中的停顿，可能延续",
    },
    WyckoffPhase.RE_DISTRIBUTION: {
        "en": "Pause in downtrend, likely continuation",
        "zh-CN": "下跌趋势中的停顿，可能延续",
    },
}


def get_phase_description(phase: WyckoffPhase, locale: str = "en") -> str:
    """Get localized phase description.

    Args:
        phase: Wyckoff phase enum value.
        locale: Language code (\"en\" or \"zh-CN\"). Defaults to \"en\".

    Returns:
        Localized description string, falling back to \"en\" if locale not found.
    """
    phase_map = PHASE_DESCRIPTIONS.get(phase, {})
    return phase_map.get(locale, phase_map.get("en", "Unknown phase"))

"""分析报告模板系统。"""

from dataclasses import dataclass
from enum import StrEnum


class ReportSection(StrEnum):
    EXECUTIVE_SUMMARY = "executive_summary"
    TECHNICAL_ANALYSIS = "technical_analysis"
    MACRO_CONTEXT = "macro_context"
    DEBATE_SUMMARY = "debate_summary"
    STRATEGY_RECOMMENDATIONS = "strategy_recommendations"
    RISK_ASSESSMENT = "risk_assessment"
    POSITION_CONTEXT = "position_context"


@dataclass
class ReportTemplate:
    sections: list[ReportSection]
    include_charts: bool = False
    max_words_per_section: int = 300
    language: str = "zh-CN"


FULL_ANALYSIS = ReportTemplate(
    sections=[section for section in ReportSection],
    max_words_per_section=500,
)

QUICK_SCAN = ReportTemplate(
    sections=[
        ReportSection.EXECUTIVE_SUMMARY,
        ReportSection.TECHNICAL_ANALYSIS,
        ReportSection.STRATEGY_RECOMMENDATIONS,
    ],
    max_words_per_section=200,
)

POSITION_REVIEW = ReportTemplate(
    sections=[
        ReportSection.TECHNICAL_ANALYSIS,
        ReportSection.POSITION_CONTEXT,
        ReportSection.RISK_ASSESSMENT,
    ],
    max_words_per_section=400,
)

SECTION_TITLES = {
    "executive_summary": "概要",
    "technical_analysis": "技术分析",
    "macro_context": "宏观环境",
    "debate_summary": "多空辩论",
    "strategy_recommendations": "策略推荐",
    "risk_assessment": "风险评估",
    "position_context": "持仓回顾",
}


def build_structured_report(sections_data: dict[str, str], template: ReportTemplate) -> dict:
    sections = []
    for section in template.sections:
        sections.append(
            {
                "id": section.value,
                "title": SECTION_TITLES.get(section.value, section.value),
                "content": sections_data.get(section.value, ""),
            }
        )

    return {
        "sections": sections,
        "metadata": {
            "language": template.language,
            "section_count": len(sections),
        },
    }


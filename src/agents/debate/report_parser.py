"""从 analysis_report 中解析结构化数据的共享工具。"""

from src.models import AgentState


def extract_technical_grade(state: AgentState) -> str:
    """从 analysis_report 中提取技术评分 Grade（A/B/C/D/F）。"""
    if not state.analysis_report:
        return "F"
    for line in state.analysis_report.split("\n"):
        if "Grade:" in line and "Total:" in line:
            try:
                return line.split("Grade:")[1].strip().split(",")[0].strip()
            except (IndexError, ValueError):
                pass
    return "F"


def extract_macro_regime(state: AgentState) -> str:
    """从 analysis_report 中提取宏观 Regime。"""
    if not state.analysis_report:
        return "neutral"
    for line in state.analysis_report.split("\n"):
        if "Regime:" in line and "Macro" not in line.split("Regime:")[0]:
            try:
                regime = line.split("Regime:")[1].strip().split("(")[0].strip()
                if regime in ("risk_on", "risk_off", "neutral"):
                    return regime
            except (IndexError, ValueError):
                pass
    return "neutral"

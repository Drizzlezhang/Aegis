"""Tests for quant brain report templates."""

from src.agents.quant_brain.report_templates import (
    FULL_ANALYSIS,
    POSITION_REVIEW,
    QUICK_SCAN,
    build_structured_report,
)


def test_full_analysis_has_7_sections():
    assert len(FULL_ANALYSIS.sections) == 7


def test_quick_scan_has_3_sections():
    assert len(QUICK_SCAN.sections) == 3


def test_position_review_has_3_sections():
    assert len(POSITION_REVIEW.sections) == 3


def test_build_structured_report():
    report = build_structured_report({"executive_summary": "概要内容"}, QUICK_SCAN)

    assert report["sections"][0] == {
        "id": "executive_summary",
        "title": "概要",
        "content": "概要内容",
    }
    assert report["sections"][1]["content"] == ""
    assert report["metadata"] == {"language": "zh-CN", "section_count": 3}


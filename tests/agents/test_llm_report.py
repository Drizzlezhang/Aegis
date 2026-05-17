"""Tests for LLM enhanced report helpers."""

import pytest

from src.agents.quant_brain import llm_integration


def test_build_analysis_prompt_complete():
    prompt = llm_integration._build_analysis_prompt(
        "AAPL",
        {"score": 82, "grade": "A", "trend": "bullish", "signals": ["RSI healthy", "MACD up"]},
        [180.0, 175.0],
        {"fair": 210},
        {"regime": "risk_on"},
    )

    assert "标的: AAPL" in prompt
    assert "技术评分: 82/100, Grade: A" in prompt
    assert "信号: RSI healthy, MACD up" in prompt
    assert "支撑位" in prompt
    assert "估值区间" in prompt
    assert "宏观环境" in prompt


def test_build_analysis_prompt_missing_fields():
    prompt = llm_integration._build_analysis_prompt("AAPL", {}, [], None, None)

    assert "技术评分: N/A/100, Grade: N/A" in prompt
    assert "趋势: N/A" in prompt
    assert "支撑位" not in prompt


@pytest.mark.asyncio
async def test_generate_report_llm_unavailable_returns_empty(monkeypatch):
    async def failing_generate(**kwargs):
        raise RuntimeError("LLM down")

    monkeypatch.setattr(llm_integration, "generate", failing_generate)

    result = await llm_integration.generate_llm_enhanced_report(
        symbol="AAPL",
        technical_summary={"score": 80, "grade": "A", "trend": "bullish"},
    )

    assert result == ""


@pytest.mark.asyncio
async def test_generate_report_success_mock(monkeypatch):
    async def fake_generate(**kwargs):
        assert kwargs["task_type"] == llm_integration.TaskType.REASONING
        assert "标的: AAPL" in kwargs["prompt"]
        return "LLM report"

    monkeypatch.setattr(llm_integration, "generate", fake_generate)

    result = await llm_integration.generate_llm_enhanced_report(
        symbol="AAPL",
        technical_summary={"score": 80, "grade": "A", "trend": "bullish"},
    )

    assert result == "LLM report"


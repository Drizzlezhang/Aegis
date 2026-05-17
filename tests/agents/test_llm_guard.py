"""Tests for LLM optional guard."""

import pytest

from src.agents.quant_brain.llm_guard import llm_optional


@pytest.mark.asyncio
async def test_llm_optional_success_passthrough():
    @llm_optional(fallback_value="fallback")
    async def success():
        return "ok"

    assert await success() == "ok"


@pytest.mark.asyncio
async def test_llm_optional_exception_returns_fallback():
    @llm_optional(fallback_value="fallback")
    async def fails():
        raise RuntimeError("LLM down")

    assert await fails() == "fallback"


@pytest.mark.asyncio
async def test_llm_optional_custom_fallback_value():
    fallback = {"status": "degraded"}

    @llm_optional(fallback_value=fallback)
    async def fails():
        raise RuntimeError("LLM down")

    assert await fails() == fallback


@pytest.mark.asyncio
async def test_llm_optional_logs_warning(caplog):
    @llm_optional(fallback_value="fallback")
    async def fails():
        raise RuntimeError("LLM down")

    assert await fails() == "fallback"
    assert "LLM call failed in fails" in caplog.text


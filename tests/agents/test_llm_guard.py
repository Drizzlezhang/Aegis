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
async def test_llm_optional_logs_warning():
    from unittest.mock import patch

    with patch("src.agents.quant_brain.llm_guard.logger.warning") as mock_warning:
        @llm_optional(fallback_value="fallback")
        async def fails():
            raise RuntimeError("LLM down")

        assert await fails() == "fallback"
        mock_warning.assert_called_once()
        assert "LLM call failed" in mock_warning.call_args[0][0]


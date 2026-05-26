"""Tests for TraceContext contextvars isolation."""

import asyncio

import pytest

from src.observability.logging import TraceContext


@pytest.mark.asyncio
async def test_trace_context_isolation_across_tasks():
    """Verify TraceContext values are isolated across concurrent asyncio tasks."""
    results: dict[str, dict] = {}

    async def task_a():
        TraceContext.set("trace-aaa", "AAPL")
        await asyncio.sleep(0.01)
        results["a"] = TraceContext.get()
        TraceContext.clear()

    async def task_b():
        TraceContext.set("trace-bbb", "TSLA")
        await asyncio.sleep(0.01)
        results["b"] = TraceContext.get()
        TraceContext.clear()

    await asyncio.gather(task_a(), task_b())

    assert results["a"]["trace_id"] == "trace-aaa"
    assert results["a"]["symbol"] == "AAPL"
    assert results["b"]["trace_id"] == "trace-bbb"
    assert results["b"]["symbol"] == "TSLA"


def test_trace_context_default():
    """Verify default value is empty dict."""
    TraceContext.clear()
    assert TraceContext.get() == {}


def test_trace_context_set_get():
    """Verify basic set/get works."""
    TraceContext.set("test-id", "TEST")
    ctx = TraceContext.get()
    assert ctx["trace_id"] == "test-id"
    assert ctx["symbol"] == "TEST"
    TraceContext.clear()

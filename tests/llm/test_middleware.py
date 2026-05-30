"""Tests for LLM governance middleware (D1)."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from src.llm.middleware import (
    GovernanceContext,
    GovernanceMiddlewareChain,
    MetricsMiddleware,
    Middleware,
    get_governance_chain,
    llm_governed,
    reset_governance_chain,
)

# ── Helpers ─────────────────────────────────────────────────────────────────


class _RecordingMiddleware(Middleware):
    """Middleware that records call order."""

    def __init__(self, name: str, records: list[str]) -> None:
        self.name = name
        self.records = records

    async def process(
        self,
        ctx: GovernanceContext,
        call_next: Callable[[GovernanceContext], Awaitable[Any]],
    ) -> Any:
        self.records.append(f"{self.name}_enter")
        result = await call_next(ctx)
        self.records.append(f"{self.name}_exit")
        return result


class _ShortCircuitMiddleware(Middleware):
    """Middleware that short-circuits without calling next."""

    def __init__(self, return_value: Any = "cached") -> None:
        self.return_value = return_value

    async def process(
        self,
        ctx: GovernanceContext,
        call_next: Callable[[GovernanceContext], Awaitable[Any]],
    ) -> Any:
        ctx.cache_hit = True
        return self.return_value


class _FailingMiddleware(Middleware):
    """Middleware that raises an exception."""

    async def process(
        self,
        ctx: GovernanceContext,
        call_next: Callable[[GovernanceContext], Awaitable[Any]],
    ) -> Any:
        raise RuntimeError("middleware failure")


# ── Tests ───────────────────────────────────────────────────────────────────


class TestGovernanceContext:
    def test_default_values(self) -> None:
        ctx = GovernanceContext(agent_name="test_agent")
        assert ctx.agent_name == "test_agent"
        assert len(ctx.request_id) == 12
        assert ctx.cache_hit is False
        assert ctx.success is True

    def test_compute_hash_deterministic(self) -> None:
        ctx1 = GovernanceContext(
            agent_name="test",
            prompt="hello",
            model="gpt-4",
            temperature=0.5,
            system_prompt="be helpful",
        )
        ctx2 = GovernanceContext(
            agent_name="test",
            prompt="hello",
            model="gpt-4",
            temperature=0.5,
            system_prompt="be helpful",
        )
        h1 = ctx1.compute_hash()
        h2 = ctx2.compute_hash()
        assert h1 == h2
        assert len(h1) == 64  # sha256 hex

    def test_compute_hash_different_prompt(self) -> None:
        ctx1 = GovernanceContext(prompt="hello", model="gpt-4")
        ctx2 = GovernanceContext(prompt="world", model="gpt-4")
        assert ctx1.compute_hash() != ctx2.compute_hash()

    def test_compute_hash_different_temperature(self) -> None:
        ctx1 = GovernanceContext(prompt="hello", model="gpt-4", temperature=0.0)
        ctx2 = GovernanceContext(prompt="hello", model="gpt-4", temperature=1.0)
        assert ctx1.compute_hash() != ctx2.compute_hash()

    def test_compute_hash_different_system_prompt(self) -> None:
        ctx1 = GovernanceContext(prompt="hello", model="gpt-4", system_prompt="a")
        ctx2 = GovernanceContext(prompt="hello", model="gpt-4", system_prompt="b")
        assert ctx1.compute_hash() != ctx2.compute_hash()

    def test_compute_hash_none_vs_empty_system_prompt(self) -> None:
        ctx1 = GovernanceContext(prompt="hello", model="gpt-4", system_prompt=None)
        ctx2 = GovernanceContext(prompt="hello", model="gpt-4", system_prompt="")
        # None and "" should produce different hashes
        assert ctx1.compute_hash() != ctx2.compute_hash()


class TestMiddlewareChain:
    async def test_empty_chain_calls_final_handler(self) -> None:
        chain = GovernanceMiddlewareChain()
        ctx = GovernanceContext(agent_name="test")

        called = False

        async def handler(c: GovernanceContext) -> str:
            nonlocal called
            called = True
            return "result"

        result = await chain.execute(ctx, handler)
        assert result == "result"
        assert called is True

    async def test_middleware_execution_order(self) -> None:
        chain = GovernanceMiddlewareChain()
        records: list[str] = []
        chain.add(_RecordingMiddleware("A", records))
        chain.add(_RecordingMiddleware("B", records))

        ctx = GovernanceContext(agent_name="test")

        async def handler(c: GovernanceContext) -> str:
            records.append("handler")
            return "done"

        result = await chain.execute(ctx, handler)
        assert result == "done"
        # Order: A_enter → B_enter → handler → B_exit → A_exit
        assert records == ["A_enter", "B_enter", "handler", "B_exit", "A_exit"]

    async def test_short_circuit_middleware(self) -> None:
        chain = GovernanceMiddlewareChain()
        records: list[str] = []
        chain.add(_ShortCircuitMiddleware(return_value="cached_result"))
        chain.add(_RecordingMiddleware("B", records))

        ctx = GovernanceContext(agent_name="test")

        async def handler(c: GovernanceContext) -> str:
            records.append("handler")
            return "should_not_reach"

        result = await chain.execute(ctx, handler)
        assert result == "cached_result"
        assert ctx.cache_hit is True
        # B and handler should NOT be called
        assert "B_enter" not in records
        assert "handler" not in records

    async def test_failing_middleware_is_skipped(self) -> None:
        chain = GovernanceMiddlewareChain()
        records: list[str] = []
        chain.add(_FailingMiddleware())
        chain.add(_RecordingMiddleware("B", records))

        ctx = GovernanceContext(agent_name="test")

        async def handler(c: GovernanceContext) -> str:
            records.append("handler")
            return "done"

        result = await chain.execute(ctx, handler)
        assert result == "done"
        # Failing middleware should be skipped, B and handler should run
        assert records == ["B_enter", "handler", "B_exit"]


class TestMetricsMiddleware:
    async def test_records_latency(self) -> None:
        chain = GovernanceMiddlewareChain()
        metrics = MetricsMiddleware()
        chain.add(metrics)

        completed_ctx: GovernanceContext | None = None

        async def on_complete(ctx: GovernanceContext) -> None:
            nonlocal completed_ctx
            completed_ctx = ctx

        metrics.set_on_complete(on_complete)

        ctx = GovernanceContext(agent_name="test")

        async def handler(c: GovernanceContext) -> str:
            await asyncio.sleep(0.01)
            return "ok"

        result = await chain.execute(ctx, handler)
        assert result == "ok"
        assert completed_ctx is not None
        assert completed_ctx.latency_ms > 0
        assert completed_ctx.success is True

    async def test_records_failure(self) -> None:
        chain = GovernanceMiddlewareChain()
        metrics = MetricsMiddleware()
        chain.add(metrics)

        completed_ctx: GovernanceContext | None = None

        async def on_complete(ctx: GovernanceContext) -> None:
            nonlocal completed_ctx
            completed_ctx = ctx

        metrics.set_on_complete(on_complete)

        ctx = GovernanceContext(agent_name="test")

        async def handler(c: GovernanceContext) -> str:
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            await chain.execute(ctx, handler)

        assert completed_ctx is not None
        assert completed_ctx.success is False
        assert completed_ctx.error_msg == "test error"


class TestDecorator:
    def setup_method(self) -> None:
        reset_governance_chain()

    def teardown_method(self) -> None:
        reset_governance_chain()

    async def test_decorator_passes_through(self) -> None:
        @llm_governed("test_agent")
        async def my_call(prompt: str, **_kwargs: Any) -> str:
            return f"echo: {prompt}"

        result = await my_call(prompt="hello")
        assert result == "echo: hello"

    async def test_decorator_injects_gov_ctx(self) -> None:
        received_ctx: GovernanceContext | None = None

        @llm_governed("test_agent")
        async def my_call(prompt: str, **_kwargs: Any) -> str:
            nonlocal received_ctx
            received_ctx = _kwargs.get("_gov_ctx")
            return "ok"

        await my_call(prompt="hello")
        assert received_ctx is not None
        assert received_ctx.agent_name == "test_agent"
        assert len(received_ctx.request_id) == 12

    async def test_decorator_governance_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When governance is disabled, the decorator should pass through directly."""
        from unittest.mock import MagicMock

        mock_config = MagicMock()
        mock_config.llm.governance.enabled = False
        monkeypatch.setattr("src.llm.middleware.get_config", lambda: mock_config)

        call_count = 0

        @llm_governed("test_agent")
        async def my_call(prompt: str, **_kwargs: Any) -> str:
            nonlocal call_count
            call_count += 1
            return f"echo: {prompt}"

        result = await my_call(prompt="hello")
        assert result == "echo: hello"
        assert call_count == 1


class TestGlobalChain:
    def setup_method(self) -> None:
        reset_governance_chain()

    def teardown_method(self) -> None:
        reset_governance_chain()

    def test_get_governance_chain_returns_same_instance(self) -> None:
        chain1 = get_governance_chain()
        chain2 = get_governance_chain()
        assert chain1 is chain2

    def test_reset_governance_chain(self) -> None:
        chain1 = get_governance_chain()
        reset_governance_chain()
        chain2 = get_governance_chain()
        assert chain1 is not chain2

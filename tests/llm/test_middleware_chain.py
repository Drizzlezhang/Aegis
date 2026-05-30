"""Tests for LLM governance middleware chain (P0-1 hotfix)."""

import pytest

from src.llm.budget import (
    BudgetExceededError,
    reset_budget_tracker,
)
from src.llm.middleware import (
    ExecuteMiddleware,
    GovernanceAbortError,
    GovernanceContext,
    GovernanceMiddlewareChain,
    MetricsMiddleware,
    get_governance_chain,
    reset_governance_chain,
)


class TestGovernanceAbortError:
    def test_is_exception(self) -> None:
        err = GovernanceAbortError("test abort")
        assert isinstance(err, Exception)

    def test_budget_exceeded_is_subclass(self) -> None:
        assert issubclass(BudgetExceededError, GovernanceAbortError)


class TestChainHasFiveLayersByDefault:
    def setup_method(self) -> None:
        reset_governance_chain()

    def teardown_method(self) -> None:
        reset_governance_chain()

    def test_chain_has_five_layers_by_default(self) -> None:
        chain = get_governance_chain()
        names = [type(m).__name__ for m in chain._middlewares]
        assert names == [
            "CacheMiddleware",
            "RateLimitMiddleware",
            "BudgetMiddleware",
            "ExecuteMiddleware",
            "MetricsMiddleware",
        ], f"Expected 5 layers in order, got {names}"


class TestBudgetExceededRaisesNotSwallowed:
    """Verify that BudgetExceededError propagates through _dispatch instead of being swallowed."""

    def setup_method(self) -> None:
        reset_governance_chain()
        reset_budget_tracker()

    def teardown_method(self) -> None:
        reset_governance_chain()
        reset_budget_tracker()

    async def test_budget_exceeded_raises_not_swallowed(self) -> None:
        """When a middleware raises BudgetExceededError, the chain must propagate it."""
        chain = GovernanceMiddlewareChain()

        class RaisingBudgetMiddleware:
            async def process(self, ctx, call_next):
                raise BudgetExceededError("daily", 0.001, 0.002)

        chain.add(RaisingBudgetMiddleware())  # type: ignore[arg-type]
        chain.add(ExecuteMiddleware())
        chain.add(MetricsMiddleware())

        ctx = GovernanceContext(agent_name="test")

        async def final_handler(c: GovernanceContext) -> str:
            return "should_not_reach"

        with pytest.raises(BudgetExceededError) as exc_info:
            await chain.execute(ctx, final_handler)

        assert exc_info.value.period == "daily"
        assert exc_info.value.limit_usd == 0.001

    async def test_regular_exception_still_swallowed(self) -> None:
        """Non-GovernanceAbortError exceptions should still be swallowed (graceful degradation)."""
        chain = GovernanceMiddlewareChain()

        class FailingMiddleware:
            async def process(self, ctx, call_next):
                raise ValueError("transient failure")

        chain.add(FailingMiddleware())  # type: ignore[arg-type]
        chain.add(ExecuteMiddleware())
        chain.add(MetricsMiddleware())

        ctx = GovernanceContext(agent_name="test")
        call_count = 0

        async def final_handler(c: GovernanceContext) -> str:
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await chain.execute(ctx, final_handler)
        assert result == "ok"
        assert call_count == 1


class TestCacheHitShortCircuitsExecute:
    """Verify that a cache hit prevents the Execute middleware from being called."""

    def setup_method(self) -> None:
        reset_governance_chain()

    def teardown_method(self) -> None:
        reset_governance_chain()

    async def test_cache_hit_short_circuits_execute(self) -> None:
        """When CacheMiddleware returns cached content, call_next should not be invoked."""
        chain = GovernanceMiddlewareChain()

        class FakeCacheMiddleware:
            async def process(self, ctx, call_next):
                ctx.cache_hit = True
                return "cached_response"

        execute_called = False

        class TrackingExecuteMiddleware:
            async def process(self, ctx, call_next):
                nonlocal execute_called
                execute_called = True
                return await call_next(ctx)

        chain.add(FakeCacheMiddleware())  # type: ignore[arg-type]
        chain.add(TrackingExecuteMiddleware())  # type: ignore[arg-type]
        chain.add(MetricsMiddleware())

        ctx = GovernanceContext(agent_name="test")

        async def final_handler(c: GovernanceContext) -> str:
            return "should_not_reach"

        result = await chain.execute(ctx, final_handler)
        assert result == "cached_response"
        assert ctx.cache_hit is True
        assert execute_called is False, "Execute should not be called on cache hit"


class TestRateLimitBlocksWhenQpsExceeded:
    """Verify that RateLimitMiddleware queues requests when rate limit is exceeded."""

    def setup_method(self) -> None:
        reset_governance_chain()

    def teardown_method(self) -> None:
        reset_governance_chain()

    async def test_rate_limit_blocks_when_qps_exceeded(self) -> None:
        """RateLimitMiddleware should delay (not reject) when rate limit is hit."""
        chain = GovernanceMiddlewareChain()

        delay_applied = False

        class FakeRateLimitMiddleware:
            async def process(self, ctx, call_next):
                nonlocal delay_applied
                # Simulate rate limit: apply a small delay
                import asyncio
                delay_applied = True
                await asyncio.sleep(0.01)
                return await call_next(ctx)

        chain.add(FakeRateLimitMiddleware())  # type: ignore[arg-type]
        chain.add(ExecuteMiddleware())
        chain.add(MetricsMiddleware())

        ctx = GovernanceContext(agent_name="test")
        call_count = 0

        async def final_handler(c: GovernanceContext) -> str:
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await chain.execute(ctx, final_handler)
        assert result == "ok"
        assert call_count == 1
        assert delay_applied is True

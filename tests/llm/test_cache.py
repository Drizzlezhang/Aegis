"""Tests for LLM prompt cache (D3)."""

import asyncio

from src.llm.cache import (
    CacheMiddleware,
    PromptCache,
    reset_prompt_cache,
)
from src.llm.middleware import GovernanceContext


class TestPromptCacheKey:
    def test_deterministic(self) -> None:
        k1 = PromptCache.cache_key("hello", "gpt-4", 0.5, "be helpful")
        k2 = PromptCache.cache_key("hello", "gpt-4", 0.5, "be helpful")
        assert k1 == k2
        assert len(k1) == 64

    def test_different_prompt(self) -> None:
        k1 = PromptCache.cache_key("hello", "gpt-4", 0.5, None)
        k2 = PromptCache.cache_key("world", "gpt-4", 0.5, None)
        assert k1 != k2

    def test_different_model(self) -> None:
        k1 = PromptCache.cache_key("hello", "gpt-4", 0.5, None)
        k2 = PromptCache.cache_key("hello", "gpt-4o", 0.5, None)
        assert k1 != k2

    def test_different_temperature(self) -> None:
        k1 = PromptCache.cache_key("hello", "gpt-4", 0.0, None)
        k2 = PromptCache.cache_key("hello", "gpt-4", 1.0, None)
        assert k1 != k2

    def test_different_system_prompt(self) -> None:
        k1 = PromptCache.cache_key("hello", "gpt-4", 0.5, "sys_a")
        k2 = PromptCache.cache_key("hello", "gpt-4", 0.5, "sys_b")
        assert k1 != k2

    def test_none_vs_empty_system_prompt(self) -> None:
        k1 = PromptCache.cache_key("hello", "gpt-4", 0.5, None)
        k2 = PromptCache.cache_key("hello", "gpt-4", 0.5, "")
        assert k1 != k2


class TestPromptCacheStats:
    def test_initial_stats(self) -> None:
        cache = PromptCache()
        assert cache.hits == 0
        assert cache.misses == 0
        assert cache.hit_rate == 0.0

    def test_hit_rate(self) -> None:
        cache = PromptCache()
        cache._hits = 30
        cache._misses = 70
        assert cache.hit_rate == 0.3

    def test_reset_stats(self) -> None:
        cache = PromptCache()
        cache._hits = 10
        cache._misses = 10
        cache.reset_stats()
        assert cache.hits == 0
        assert cache.misses == 0


class TestCacheMiddleware:
    def setup_method(self) -> None:
        reset_prompt_cache()

    def teardown_method(self) -> None:
        reset_prompt_cache()

    async def test_cache_hit_short_circuits(self) -> None:
        cache = PromptCache()
        key = PromptCache.cache_key("test prompt", "gpt-4", 0.5, None)
        await cache.set(key, {"content": "cached response"})

        middleware = CacheMiddleware(cache=cache)
        ctx = GovernanceContext(
            agent_name="test",
            prompt="test prompt",
            model="gpt-4",
            temperature=0.5,
        )

        call_count = 0

        async def call_next(c: GovernanceContext) -> str:
            nonlocal call_count
            call_count += 1
            return "real response"

        result = await middleware.process(ctx, call_next)
        assert result == "cached response"
        assert ctx.cache_hit is True
        assert call_count == 0  # Should NOT call LLM

    async def test_cache_miss_calls_next(self) -> None:
        cache = PromptCache()
        middleware = CacheMiddleware(cache=cache)
        ctx = GovernanceContext(
            agent_name="test",
            prompt="new prompt",
            model="gpt-4",
            temperature=0.5,
        )

        call_count = 0

        async def call_next(c: GovernanceContext) -> str:
            nonlocal call_count
            call_count += 1
            return "real response"

        result = await middleware.process(ctx, call_next)
        assert result == "real response"
        assert ctx.cache_hit is False
        assert call_count == 1

    async def test_excluded_agent_skips_cache(self) -> None:
        cache = PromptCache()
        key = PromptCache.cache_key("test", "gpt-4", 0.5, None)
        await cache.set(key, {"content": "cached"})

        middleware = CacheMiddleware(cache=cache)
        middleware._exclude_agents = ["debate"]

        ctx = GovernanceContext(
            agent_name="debate",
            prompt="test",
            model="gpt-4",
            temperature=0.5,
        )

        call_count = 0

        async def call_next(c: GovernanceContext) -> str:
            nonlocal call_count
            call_count += 1
            return "real"

        result = await middleware.process(ctx, call_next)
        assert result == "real"
        assert call_count == 1  # Should call LLM despite cache

    async def test_cache_miss_then_hit(self) -> None:
        """Second call with same params should hit cache."""
        cache = PromptCache()
        middleware = CacheMiddleware(cache=cache)

        ctx1 = GovernanceContext(
            agent_name="test",
            prompt="repeat",
            model="gpt-4",
            temperature=0.5,
        )

        call_count = 0

        async def call_next(c: GovernanceContext) -> str:
            nonlocal call_count
            call_count += 1
            return f"response_{call_count}"

        # First call — miss
        result1 = await middleware.process(ctx1, call_next)
        assert result1 == "response_1"
        assert call_count == 1

        # Second call — should hit cache
        ctx2 = GovernanceContext(
            agent_name="test",
            prompt="repeat",
            model="gpt-4",
            temperature=0.5,
        )
        result2 = await middleware.process(ctx2, call_next)
        assert result2 == "response_1"  # Cached value
        assert call_count == 1  # No additional call

    async def test_concurrent_dedup(self) -> None:
        """Concurrent requests with same key should only execute once."""
        cache = PromptCache()
        middleware = CacheMiddleware(cache=cache)

        call_count = 0

        async def call_next(c: GovernanceContext) -> str:
            nonlocal call_count
            await asyncio.sleep(0.05)  # Simulate LLM latency
            call_count += 1
            return f"response_{call_count}"

        async def make_call() -> str:
            ctx = GovernanceContext(
                agent_name="test",
                prompt="concurrent",
                model="gpt-4",
                temperature=0.5,
            )
            return await middleware.process(ctx, call_next)

        # Launch 5 concurrent calls
        results = await asyncio.gather(*[make_call() for _ in range(5)])

        # Only 1 actual LLM call should have been made
        assert call_count == 1
        # All results should be non-empty strings
        assert all(isinstance(r, str) and len(r) > 0 for r in results)

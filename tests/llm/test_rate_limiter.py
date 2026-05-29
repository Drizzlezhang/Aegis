"""Tests for LLM rate limiter (D4)."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from src.llm.middleware import GovernanceContext
from src.llm.rate_limiter import RateLimitMiddleware, TokenBucket


class TestTokenBucket:
    def test_initial_tokens(self) -> None:
        bucket = TokenBucket(rps=10)
        assert bucket.available_tokens == 10.0

    async def test_acquire_immediate(self) -> None:
        bucket = TokenBucket(rps=10)
        wait = await bucket.acquire()
        assert wait == 0.0
        assert bucket.available_tokens == pytest.approx(9.0)

    async def test_acquire_multiple(self) -> None:
        bucket = TokenBucket(rps=10)
        for _ in range(5):
            wait = await bucket.acquire()
            assert wait == 0.0
        assert bucket.available_tokens == pytest.approx(5.0, rel=0.01)

    async def test_burst_exceeds_capacity(self) -> None:
        """Burst N+5 requests, the N+1th should have wait_ms > 0."""
        bucket = TokenBucket(rps=10)
        # Acquire all tokens
        for _ in range(10):
            wait = await bucket.acquire()
            assert wait == 0.0

        # Next request should wait
        wait = await bucket.acquire()
        assert wait > 0

    async def test_refill_over_time(self) -> None:
        bucket = TokenBucket(rps=100)  # 100 tokens/sec
        # Drain all tokens
        for _ in range(100):
            await bucket.acquire()

        assert bucket.available_tokens < 1.0

        # Wait for refill
        await asyncio.sleep(0.05)  # 50ms → ~5 tokens

        # Should be able to acquire without waiting
        wait = await bucket.acquire()
        assert wait == 0.0


class TestRateLimitMiddleware:
    async def test_passes_through_when_no_limit(self) -> None:
        middleware = RateLimitMiddleware()
        ctx = GovernanceContext(agent_name="test", provider="deepseek")

        call_count = 0

        async def call_next(c: GovernanceContext) -> str:
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await middleware.process(ctx, call_next)
        assert result == "ok"
        assert call_count == 1

    async def test_multiple_requests_queued(self) -> None:
        middleware = RateLimitMiddleware()
        # Set a very low RPS for testing
        bucket = middleware.get_bucket("deepseek")
        bucket._rps = 2
        bucket._max_tokens = 2.0
        bucket._tokens = 2.0

        call_count = 0

        async def call_next(c: GovernanceContext) -> str:
            nonlocal call_count
            call_count += 1
            return "ok"

        async def make_call() -> str:
            ctx = GovernanceContext(agent_name="test", provider="deepseek")
            return await middleware.process(ctx, call_next)

        start = time.monotonic()
        results = await asyncio.gather(*[make_call() for _ in range(5)])
        elapsed = time.monotonic() - start

        assert all(r == "ok" for r in results)
        assert call_count == 5
        # With RPS=2, 5 requests should take at least some time
        # (first 2 immediate, next 3 need to wait for tokens)
        assert elapsed > 0.1  # At least some waiting happened

    async def test_different_providers_independent(self) -> None:
        middleware = RateLimitMiddleware()
        bucket_a = middleware.get_bucket("deepseek")
        bucket_b = middleware.get_bucket("openai")

        # Drain deepseek
        bucket_a._tokens = 0.0

        # openai should still have tokens
        assert bucket_b.available_tokens > 0

        # Request to openai should pass immediately
        ctx = GovernanceContext(agent_name="test", provider="openai")

        async def call_next(c: GovernanceContext) -> str:
            return "ok"

        result = await middleware.process(ctx, call_next)
        assert result == "ok"

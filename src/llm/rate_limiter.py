"""Token bucket rate limiter for LLM governance.

Provides RateLimitMiddleware that enforces per-provider rate limits using
a token bucket algorithm. Excess requests are queued (asyncio.Queue) rather
than rejected.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from src.config import get_config

from .middleware import GovernanceContext, Middleware

logger = logging.getLogger(__name__)


# ── Token Bucket ─────────────────────────────────────────────────────────────


class TokenBucket:
    """Token bucket rate limiter for a single provider."""

    def __init__(self, rps: int = 10, tpm: int = 100000) -> None:
        self._rps = rps
        self._tpm = tpm
        self._tokens = float(rps)
        self._max_tokens = float(rps)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()
        # Per-minute token tracking
        self._minute_tokens = 0
        self._minute_start = time.monotonic()

    @property
    def rps(self) -> int:
        return self._rps

    @property
    def available_tokens(self) -> float:
        return self._tokens

    async def acquire(self) -> float:
        """Acquire a token. Returns wait time in seconds (0 if immediate)."""
        async with self._lock:
            now = time.monotonic()
            self._refill(now)

            if self._tokens >= 1.0:
                self._tokens -= 1.0
                self._minute_tokens += 1
                return 0.0

            # Calculate wait time
            wait_time = (1.0 - self._tokens) / self._rps
            self._tokens -= 1.0
            self._minute_tokens += 1
            return wait_time

    def _refill(self, now: float) -> None:
        """Refill tokens based on elapsed time."""
        elapsed = now - self._last_refill
        self._tokens = min(self._max_tokens, self._tokens + elapsed * self._rps)
        self._last_refill = now

        # Reset minute counter if a minute has passed
        if now - self._minute_start >= 60.0:
            self._minute_tokens = 0
            self._minute_start = now


# ── Rate Limit Middleware ────────────────────────────────────────────────────


class RateLimitMiddleware(Middleware):
    """Middleware that enforces per-provider token bucket rate limits."""

    def __init__(self) -> None:
        config = get_config()
        governance = getattr(config.llm, "governance", None)
        rate_limits: dict[str, dict[str, int]] = (
            getattr(governance, "rate_limit", {}) if governance else {}
        )
        self._buckets: dict[str, TokenBucket] = {}
        for provider, limits in rate_limits.items():
            rps = limits.get("rps", 10)
            tpm = limits.get("tpm", 100000)
            self._buckets[provider] = TokenBucket(rps=rps, tpm=tpm)

    def get_bucket(self, provider: str) -> TokenBucket:
        """Get or create a token bucket for a provider."""
        if provider not in self._buckets:
            self._buckets[provider] = TokenBucket(rps=10, tpm=100000)
        return self._buckets[provider]

    async def process(
        self,
        ctx: GovernanceContext,
        call_next: Callable[[GovernanceContext], Awaitable[Any]],
    ) -> Any:
        provider = ctx.provider or "default"
        bucket = self.get_bucket(provider)

        wait_time = await bucket.acquire()

        if wait_time > 0:
            logger.debug("Rate limit wait for %s: %.1fms", provider, wait_time * 1000)
            # Record wait metric
            try:
                from src.services.metrics import record_llm_rate_limit_wait
                record_llm_rate_limit_wait(provider, wait_time * 1000)
            except Exception:
                pass
            await asyncio.sleep(wait_time)

        return await call_next(ctx)

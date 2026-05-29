"""Prompt hash cache for LLM governance.

Provides CacheMiddleware that short-circuits LLM calls when a matching
cached response exists. Cache key = sha256(prompt + model + temperature + system_prompt).

Backend: SQLite (default) via the existing async session factory.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from src.config import get_config
from src.db import get_session

from .middleware import GovernanceContext, Middleware

logger = logging.getLogger(__name__)


# ── Prompt Cache ─────────────────────────────────────────────────────────────


class PromptCache:
    """SQLite-backed prompt response cache with TTL and dedup."""

    def __init__(self, ttl_seconds: int = 86400) -> None:
        self._ttl = ttl_seconds
        self._pending: dict[str, asyncio.Event] = {}
        self._pending_results: dict[str, Any] = {}
        self._hits: int = 0
        self._misses: int = 0
        self._lock = asyncio.Lock()

    @property
    def ttl(self) -> int:
        return self._ttl

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total

    @staticmethod
    def cache_key(prompt: str, model: str, temperature: float | None, system_prompt: str | None) -> str:
        """Compute deterministic cache key."""
        sys_repr = "<None>" if system_prompt is None else system_prompt
        raw = f"{prompt}|{model}|{temperature}|{sys_repr}"
        return hashlib.sha256(raw.encode()).hexdigest()

    async def get(self, key: str) -> dict[str, Any] | None:
        """Retrieve cached response. Returns None if not found or expired."""
        async with get_session() as session:
            from sqlalchemy import text

            result = await session.execute(
                text(
                    "SELECT response_json, expires_at FROM llm_prompt_cache "
                    "WHERE cache_key = :key"
                ),
                {"key": key},
            )
            row = result.fetchone()

            if row is None:
                self._misses += 1
                return None

            response_json, expires_at = row
            if expires_at is not None:
                expires_ts = float(expires_at) if isinstance(expires_at, (int, float)) else expires_at.timestamp()
                if time.time() > expires_ts:
                    # Expired — delete and return None
                    await session.execute(
                        text("DELETE FROM llm_prompt_cache WHERE cache_key = :key"),
                        {"key": key},
                    )
                    await session.commit()
                    self._misses += 1
                    return None

            self._hits += 1
            return json.loads(response_json)

    async def set(self, key: str, response: dict[str, Any]) -> None:
        """Store a response in the cache."""
        expires_at = time.time() + self._ttl
        async with get_session() as session:
            from sqlalchemy import text

            await session.execute(
                text(
                    "INSERT OR REPLACE INTO llm_prompt_cache (cache_key, response_json, expires_at) "
                    "VALUES (:key, :response, :expires)"
                ),
                {
                    "key": key,
                    "response": json.dumps(response),
                    "expires": expires_at,
                },
            )
            await session.commit()

    async def get_or_wait(self, key: str) -> tuple[dict[str, Any] | None, bool]:
        """Get cached value or register as waiter for dedup.

        Returns (cached_value, is_leader).
        - If cached: (value, True) — use directly.
        - If not cached and no pending: (None, True) — caller is leader, must execute.
        - If not cached and pending: (None, False) — caller waits for leader.
        """
        # Check cache first
        cached = await self.get(key)
        if cached is not None:
            return cached, True

        async with self._lock:
            if key in self._pending:
                # Another caller is already fetching — wait
                event = self._pending[key]
                is_leader = False
            else:
                # This caller is the leader
                event = asyncio.Event()
                self._pending[key] = event
                is_leader = True

        if not is_leader:
            await event.wait()
            result = self._pending_results.get(key)
            return result, False

        return None, True

    def notify_waiters(self, key: str, result: dict[str, Any]) -> None:
        """Notify waiting callers that the result is ready."""
        self._pending_results[key] = result
        event = self._pending.pop(key, None)
        if event:
            event.set()

    def cancel_waiters(self, key: str) -> None:
        """Cancel waiting callers (on error)."""
        self._pending_results.pop(key, None)
        event = self._pending.pop(key, None)
        if event:
            event.set()

    def reset_stats(self) -> None:
        """Reset hit/miss counters (for testing)."""
        self._hits = 0
        self._misses = 0


# ── Cache Middleware ─────────────────────────────────────────────────────────


class CacheMiddleware(Middleware):
    """Middleware that checks prompt cache before calling LLM."""

    def __init__(self, cache: PromptCache | None = None) -> None:
        config = get_config()
        governance = getattr(config.llm, "governance", None)
        ttl = getattr(governance, "cache_ttl_seconds", 86400) if governance else 86400
        self._cache = cache or PromptCache(ttl_seconds=ttl)
        self._exclude_agents: list[str] = (
            getattr(governance, "cache_exclude_agents", ["debate"]) if governance else ["debate"]
        )

    @property
    def cache(self) -> PromptCache:
        return self._cache

    async def process(
        self,
        ctx: GovernanceContext,
        call_next: Callable[[GovernanceContext], Awaitable[Any]],
    ) -> Any:
        # Skip cache for excluded agents
        if ctx.agent_name in self._exclude_agents:
            return await call_next(ctx)

        # Compute cache key
        key = PromptCache.cache_key(ctx.prompt, ctx.model, ctx.temperature, ctx.system_prompt)
        ctx.prompt_hash = key

        # Check cache with dedup
        cached, is_leader = await self._cache.get_or_wait(key)

        if cached is not None and is_leader:
            # Cache hit — short circuit
            ctx.cache_hit = True
            return cached.get("content", "")

        if not is_leader:
            # Waiter — result was set by leader
            if cached is not None:
                ctx.cache_hit = True
                return cached.get("content", "")
            # Leader failed, fall through to execute
            return await call_next(ctx)

        # Leader — execute and cache
        try:
            result = await call_next(ctx)
            # Cache the result
            cache_data = {"content": str(result), "cached_at": time.time()}
            await self._cache.set(key, cache_data)
            self._cache.notify_waiters(key, cache_data)
            return result
        except Exception:
            self._cache.cancel_waiters(key)
            raise


# ── Global Cache ─────────────────────────────────────────────────────────────

_cache_instance: PromptCache | None = None


def get_prompt_cache() -> PromptCache:
    """Get or create the global prompt cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = PromptCache()
    return _cache_instance


def reset_prompt_cache() -> None:
    """Reset the global prompt cache (for testing)."""
    global _cache_instance
    _cache_instance = None

"""LLM governance middleware — Chain of Responsibility pattern.

Provides a pluggable middleware chain that wraps LLMClient.generate() with:
  CacheMiddleware → RateLimitMiddleware → BudgetMiddleware → ExecuteMiddleware → MetricsMiddleware

Usage:
    from src.llm.middleware import llm_governed

    @llm_governed("debate")
    async def my_llm_call(prompt: str) -> str:
        ...
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from functools import wraps
from typing import Any

from src.config import get_config

logger = logging.getLogger(__name__)


# ── Governance Context ──────────────────────────────────────────────────────


@dataclass
class GovernanceContext:
    """Context passed through the middleware chain for a single LLM call."""

    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    agent_name: str = "unknown"
    provider: str = ""
    model: str = ""
    prompt: str = ""
    system_prompt: str | None = None
    temperature: float | None = None
    prompt_hash: str = ""
    start_time: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    cache_hit: bool = False
    prompt_version: str | None = None
    success: bool = True
    error_msg: str | None = None
    bypass_budget: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def compute_hash(self) -> str:
        """Compute deterministic hash from prompt + model + temperature + system_prompt."""
        sys_repr = "<None>" if self.system_prompt is None else self.system_prompt
        raw = f"{self.prompt}|{self.model}|{self.temperature}|{sys_repr}"
        self.prompt_hash = hashlib.sha256(raw.encode()).hexdigest()
        return self.prompt_hash


# ── Middleware Base ──────────────────────────────────────────────────────────


class Middleware(ABC):
    """Abstract base for governance middleware."""

    @abstractmethod
    async def process(
        self,
        ctx: GovernanceContext,
        call_next: Callable[[GovernanceContext], Awaitable[Any]],
    ) -> Any:
        """Process the request. Call `call_next(ctx)` to pass to next middleware."""
        ...


# ── Middleware Chain ─────────────────────────────────────────────────────────


class GovernanceMiddlewareChain:
    """Chain of Responsibility for LLM governance middleware."""

    def __init__(self) -> None:
        self._middlewares: list[Middleware] = []

    def add(self, middleware: Middleware) -> GovernanceMiddlewareChain:
        """Append a middleware to the chain."""
        self._middlewares.append(middleware)
        return self

    async def execute(self, ctx: GovernanceContext, final_handler: Callable[[GovernanceContext], Awaitable[Any]]) -> Any:
        """Execute the middleware chain, ending with final_handler."""
        if not self._middlewares:
            return await final_handler(ctx)

        async def _dispatch(index: int, context: GovernanceContext) -> Any:
            if index >= len(self._middlewares):
                return await final_handler(context)
            middleware = self._middlewares[index]

            async def _next(c: GovernanceContext) -> Any:
                return await _dispatch(index + 1, c)

            try:
                return await middleware.process(context, _next)
            except Exception:
                logger.exception(
                    "Middleware %s failed for request %s, skipping to next",
                    type(middleware).__name__,
                    context.request_id,
                )
                return await _dispatch(index + 1, context)

        return await _dispatch(0, ctx)


# ── Execute Middleware (always present) ──────────────────────────────────────


class ExecuteMiddleware(Middleware):
    """Calls the actual LLM via the provided handler."""

    async def process(
        self,
        ctx: GovernanceContext,
        call_next: Callable[[GovernanceContext], Awaitable[Any]],
    ) -> Any:
        return await call_next(ctx)


# ── Metrics Middleware (always present) ──────────────────────────────────────


class MetricsMiddleware(Middleware):
    """Records metrics after the LLM call completes."""

    def __init__(self) -> None:
        self._on_complete: Callable[[GovernanceContext], Awaitable[None]] | None = None

    def set_on_complete(self, handler: Callable[[GovernanceContext], Awaitable[None]]) -> None:
        """Register a callback invoked after each LLM call."""
        self._on_complete = handler

    async def process(
        self,
        ctx: GovernanceContext,
        call_next: Callable[[GovernanceContext], Awaitable[Any]],
    ) -> Any:
        ctx.start_time = time.monotonic()
        try:
            result = await call_next(ctx)
            ctx.success = True
            return result
        except Exception as exc:
            ctx.success = False
            ctx.error_msg = str(exc)
            raise
        finally:
            ctx.latency_ms = int((time.monotonic() - ctx.start_time) * 1000)
            if self._on_complete:
                try:
                    await self._on_complete(ctx)
                except Exception:
                    logger.exception("Metrics on_complete handler failed for %s", ctx.request_id)


# ── Decorator ────────────────────────────────────────────────────────────────


def llm_governed(agent_name: str):
    """Decorator that wraps an LLM call function with governance middleware.

    Usage:
        @llm_governed("debate")
        async def call_llm(prompt: str, system_prompt: str | None = None, ...) -> str:
            ...

    The decorated function receives an additional `_gov_ctx` keyword argument
    containing the GovernanceContext, which middleware can inspect/modify.
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            config = get_config()
            governance_enabled = getattr(
                getattr(getattr(config, "llm", None), "governance", None),
                "enabled",
                True,
            )

            if not governance_enabled:
                return await func(*args, **kwargs)

            chain = get_governance_chain()

            ctx = GovernanceContext(agent_name=agent_name)

            async def _final_handler(c: GovernanceContext) -> Any:
                kwargs["_gov_ctx"] = c
                return await func(*args, **kwargs)

            return await chain.execute(ctx, _final_handler)

        return wrapper

    return decorator


# ── Global Chain ─────────────────────────────────────────────────────────────


_governance_chain: GovernanceMiddlewareChain | None = None
_chain_lock = asyncio.Lock()


def get_governance_chain() -> GovernanceMiddlewareChain:
    """Get or create the global governance middleware chain."""
    global _governance_chain
    if _governance_chain is None:
        _governance_chain = GovernanceMiddlewareChain()
        # Always add Execute and Metrics as the last two middlewares
        _governance_chain.add(ExecuteMiddleware())
        _governance_chain.add(MetricsMiddleware())
    return _governance_chain


def reset_governance_chain() -> None:
    """Reset the global governance chain (for testing)."""
    global _governance_chain
    _governance_chain = None

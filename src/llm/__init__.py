"""LLM module for Aegis."""

from .budget import BudgetExceededError, BudgetMiddleware
from .cache import CacheMiddleware
from .client import (
    LLMClient,
    LLMError,
    LLMRequest,
    LLMResponse,
    generate,
    generate_stream,
    get_client,
)
from .middleware import (
    ExecuteMiddleware,
    GovernanceAbortError,
    GovernanceContext,
    GovernanceMiddlewareChain,
    MetricsMiddleware,
    Middleware,
    get_governance_chain,
    llm_governed,
    reset_governance_chain,
)
from .rate_limiter import RateLimitMiddleware

__all__ = [
    # Client
    "LLMRequest",
    "LLMResponse",
    "LLMError",
    "LLMClient",
    "get_client",
    "generate",
    "generate_stream",

    # Middleware
    "GovernanceAbortError",
    "GovernanceContext",
    "GovernanceMiddlewareChain",
    "Middleware",
    "ExecuteMiddleware",
    "MetricsMiddleware",
    "CacheMiddleware",
    "RateLimitMiddleware",
    "BudgetMiddleware",
    "BudgetExceededError",
    "get_governance_chain",
    "llm_governed",
    "reset_governance_chain",
]

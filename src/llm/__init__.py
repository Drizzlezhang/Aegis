"""LLM module for Aegis-Trader."""

from .client import (
    LLMClient,
    LLMError,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    generate,
    generate_stream,
    get_client,
)
from .middleware import (
    GovernanceContext,
    GovernanceMiddlewareChain,
    Middleware,
    ExecuteMiddleware,
    MetricsMiddleware,
    get_governance_chain,
    llm_governed,
    reset_governance_chain,
)
from .router import LLMRouter, ModelRouting, TaskType, get_router

__all__ = [
    # Router
    "TaskType",
    "ModelRouting",
    "LLMRouter",
    "get_router",

    # Client
    "LLMProvider",
    "LLMRequest",
    "LLMResponse",
    "LLMError",
    "LLMClient",
    "get_client",
    "generate",
    "generate_stream",

    # Middleware
    "GovernanceContext",
    "GovernanceMiddlewareChain",
    "Middleware",
    "ExecuteMiddleware",
    "MetricsMiddleware",
    "get_governance_chain",
    "llm_governed",
    "reset_governance_chain",
]

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
    "generate_stream"
]

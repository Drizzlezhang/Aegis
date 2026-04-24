"""LLM module for Aegis-Trader."""

from .router import TaskType, ModelRouting, LLMRouter, get_router
from .client import LLMProvider, LLMRequest, LLMResponse, LLMError, LLMClient, get_client, generate, generate_stream

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

"""LLM 调用保护 — graceful degradation。"""

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


def llm_optional(fallback_value: Any = "") -> Callable:
    """Decorator returning fallback when an async LLM call fails."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as exc:
                logger.warning("LLM call failed in %s: %s. Using fallback.", func.__name__, exc)
                return fallback_value

        return wrapper

    return decorator


"""LLM pricing table — single model → price mapping."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Price per 1k tokens: {model: {"input": USD, "output": USD}}
_PRICE_PER_1K_TOKENS: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "deepseek-v3.2": {"input": 0.50, "output": 1.50},
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    "gemini-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "glm5.1": {"input": 0.40, "output": 1.20},
    "glm-4": {"input": 0.10, "output": 0.10},
    "kimi": {"input": 0.60, "output": 1.80},
    "minimax-2.7": {"input": 0.30, "output": 0.80},
}


def price_for(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate cost in USD for an LLM call.

    Args:
        model: Model name (e.g. "gpt-4o-mini")
        prompt_tokens: Number of input/prompt tokens
        completion_tokens: Number of output/completion tokens

    Returns:
        Total cost in USD. Returns 0.0 if model not found.
    """
    pricing = _PRICE_PER_1K_TOKENS.get(model)
    if not pricing:
        logger.debug("No pricing found for model %s, defaulting to 0.0", model)
        return 0.0

    input_cost = (prompt_tokens / 1000.0) * pricing["input"]
    output_cost = (completion_tokens / 1000.0) * pricing["output"]
    return round(input_cost + output_cost, 8)


def estimate_tokens(text: str, model: str = "gpt-4o") -> int:
    """Estimate token count for a text string.

    Uses tiktoken if available, falls back to character-based estimate.
    """
    try:
        import tiktoken
    except ImportError:
        logger.debug("tiktoken not available, using character-based estimate")
        return max(1, len(text) // 4)

    encoding_name = "o200k_base" if model.startswith("gpt-4o") else "cl100k_base"
    try:
        encoding = tiktoken.get_encoding(encoding_name)
        return len(encoding.encode(text))
    except Exception:
        return max(1, len(text) // 4)

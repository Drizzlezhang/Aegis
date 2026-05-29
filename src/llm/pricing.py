"""LLM pricing table and token estimation.

Maintains per-provider × per-model pricing (USD per 1k tokens) and provides
token counting via tiktoken.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ── Pricing Table ────────────────────────────────────────────────────────────
# Format: {provider: {model: {"input": USD/1k, "output": USD/1k}}}

PRICING_TABLE: dict[str, dict[str, dict[str, float]]] = {
    "deepseek": {
        "deepseek-v3.2": {"input": 0.50, "output": 1.50},
        "deepseek-chat": {"input": 0.14, "output": 0.28},
    },
    "glm": {
        "glm5.1": {"input": 0.40, "output": 1.20},
        "glm-4": {"input": 0.10, "output": 0.10},
    },
    "kimi": {
        "kimi": {"input": 0.60, "output": 1.80},
    },
    "gemini": {
        "gemini-pro": {"input": 1.25, "output": 5.00},
        "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
        "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    },
    "minimax": {
        "minimax-2.7": {"input": 0.30, "output": 0.80},
    },
    "openai": {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    },
    "anthropic": {
        "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
        "claude-3-haiku": {"input": 0.25, "output": 1.25},
    },
}

# Per-million-tokens pricing (used by some providers)
PRICING_PER_MILLION: dict[str, dict[str, dict[str, float]]] = {
    "deepseek": {
        "deepseek-v3.2": {"input": 0.50, "output": 1.50},
    },
}


def get_price(provider: str, model: str, token_type: str = "input") -> float:
    """Get price per 1k tokens for a given provider/model/type.

    Args:
        provider: Provider name (e.g. "deepseek", "openai")
        model: Model name (e.g. "deepseek-v3.2", "gpt-4o")
        token_type: "input" or "output"

    Returns:
        Price in USD per 1000 tokens. Returns 0.0 if not found.
    """
    provider_pricing = PRICING_TABLE.get(provider, {})
    model_pricing = provider_pricing.get(model, {})
    price = model_pricing.get(token_type, 0.0)

    if price == 0.0:
        logger.debug("No pricing found for %s/%s/%s, defaulting to 0.0", provider, model, token_type)

    return price


def calculate_cost(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Calculate total cost in USD for an LLM call.

    Args:
        provider: Provider name
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Total cost in USD.
    """
    input_price = get_price(provider, model, "input")
    output_price = get_price(provider, model, "output")

    input_cost = (input_tokens / 1000.0) * input_price
    output_cost = (output_tokens / 1000.0) * output_price

    return round(input_cost + output_cost, 8)


# ── Token Estimation ─────────────────────────────────────────────────────────

# tiktoken encoding name → model mapping
_TIKTOKEN_ENCODING_MAP: dict[str, str] = {
    "gpt-4o": "o200k_base",
    "gpt-4o-mini": "o200k_base",
    "gpt-4": "cl100k_base",
    "gpt-3.5-turbo": "cl100k_base",
    "claude-3-5-sonnet": "cl100k_base",  # approximate
    "claude-3-haiku": "cl100k_base",      # approximate
    "gemini-pro": "cl100k_base",          # approximate
    "gemini-1.5-pro": "cl100k_base",      # approximate
    "gemini-1.5-flash": "cl100k_base",    # approximate
    "deepseek-v3.2": "cl100k_base",       # approximate
    "deepseek-chat": "cl100k_base",       # approximate
    "glm5.1": "cl100k_base",              # approximate
    "glm-4": "cl100k_base",               # approximate
    "kimi": "cl100k_base",                # approximate
    "minimax-2.7": "cl100k_base",         # approximate
}


def estimate_tokens(text: str, model: str = "gpt-4o") -> int:
    """Estimate token count for a text string using tiktoken.

    Args:
        text: The text to count tokens for.
        model: Model name to select encoding. Falls back to cl100k_base.

    Returns:
        Estimated token count.
    """
    try:
        import tiktoken
    except ImportError:
        logger.warning("tiktoken not available, using character-based estimate")
        return _fallback_estimate(text)

    encoding_name = _TIKTOKEN_ENCODING_MAP.get(model, "cl100k_base")

    try:
        encoding = tiktoken.get_encoding(encoding_name)
        return len(encoding.encode(text))
    except Exception:
        logger.debug("tiktoken encoding %s failed, falling back to cl100k_base", encoding_name)
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception:
            return _fallback_estimate(text)


def _fallback_estimate(text: str) -> int:
    """Character-based fallback token estimate (~4 chars per token)."""
    return max(1, len(text) // 4)

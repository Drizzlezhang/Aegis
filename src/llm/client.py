"""Single-provider LLM client (OpenAI-compatible API)."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any

import httpx

from src.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class LLMRequest:
    """LLM request configuration."""
    prompt: str
    system_prompt: str | None = None
    model: str | None = None
    max_tokens: int = 1024
    temperature: float = 0.0
    top_p: float | None = None
    stream: bool = False
    stop: list[str] | None = None
    tools: list[dict[str, Any]] | None = None
    extra_params: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """LLM response data."""
    content: str
    model: str
    usage: dict[str, int]
    finish_reason: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


class LLMError(Exception):
    """LLM client error."""
    pass


class LLMClient:
    """Single-provider LLM client using OpenAI-compatible API."""

    def __init__(self, base_url: str, api_key: str, timeout: float = 60.0):
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Aegis/1.0",
            },
            timeout=httpx.Timeout(timeout),
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def generate(self, req: LLMRequest) -> LLMResponse:
        """Generate a completion (non-streaming)."""
        payload = self._build_payload(req)
        endpoint = "/chat/completions"

        response = await self._client.post(endpoint, json=payload)
        if response.status_code >= 400:
            text = response.text
            logger.error("LLM API error %s: %s", response.status_code, text)
            raise LLMError(f"API error {response.status_code}: {text}")

        data = response.json()
        choice = data["choices"][0]
        message = choice["message"]

        return LLMResponse(
            content=message.get("content", ""),
            model=data.get("model", req.model or "unknown"),
            usage=data.get("usage", {}),
            finish_reason=choice.get("finish_reason"),
            tool_calls=message.get("tool_calls"),
        )

    async def generate_stream(self, req: LLMRequest) -> AsyncGenerator[str, None]:
        """Generate a streaming completion."""
        payload = self._build_payload(req)
        payload["stream"] = True
        endpoint = "/chat/completions"

        async with self._client.stream("POST", endpoint, json=payload) as response:
            if response.status_code >= 400:
                text = await response.aread()
                raise LLMError(f"API error {response.status_code}: {text.decode()}")

            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk["choices"][0].get("delta", {})
                    if "content" in delta:
                        yield delta["content"]
                except (json.JSONDecodeError, KeyError, IndexError):
                    logger.debug("Failed to parse stream chunk: %s", data_str)

    def _build_payload(self, req: LLMRequest) -> dict[str, Any]:
        config = get_config()
        model = req.model or config.llm_default_model

        messages: list[dict[str, str]] = []
        if req.system_prompt:
            messages.append({"role": "system", "content": req.system_prompt})
        messages.append({"role": "user", "content": req.prompt})

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
        }
        if req.top_p is not None:
            payload["top_p"] = req.top_p
        if req.stop:
            payload["stop"] = req.stop
        if req.tools:
            payload["tools"] = req.tools
        if req.extra_params:
            payload.update(req.extra_params)
        return payload


# ── Global client ────────────────────────────────────────────────────────────

_default_client: LLMClient | None = None


def get_client() -> LLMClient:
    """Get or create the global LLM client."""
    global _default_client
    if _default_client is None:
        config = get_config()
        _default_client = LLMClient(
            base_url=config.llm_base_url,
            api_key=config.llm_api_key,
            timeout=config.llm_timeout_seconds,
        )
    return _default_client


async def generate(
    prompt: str,
    system_prompt: str | None = None,
    model: str | None = None,
    **kwargs: Any,
) -> str:
    """Convenience function for simple text generation."""
    req = LLMRequest(prompt=prompt, system_prompt=system_prompt, model=model, **kwargs)
    client = get_client()
    try:
        response = await client.generate(req)
        return response.content
    finally:
        pass  # client is shared, don't close


async def generate_stream(
    prompt: str,
    system_prompt: str | None = None,
    model: str | None = None,
    **kwargs: Any,
) -> AsyncGenerator[str, None]:
    """Convenience function for streaming text generation."""
    req = LLMRequest(prompt=prompt, system_prompt=system_prompt, model=model, **kwargs)
    client = get_client()
    async for chunk in client.generate_stream(req):
        yield chunk

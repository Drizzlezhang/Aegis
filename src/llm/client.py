"""Unified LLM client for multi-provider support."""

import json
import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import aiohttp

from src.config import get_config

from .router import ModelRouting, TaskType, get_router

logger = logging.getLogger(__name__)


class LLMProvider(StrEnum):
    """LLM provider enumeration."""
    DEEPSEEK = "deepseek"
    GLM = "glm"
    KIMI = "kimi"
    GEMINI = "gemini"
    MINIMAX = "minimax"


@dataclass
class LLMRequest:
    """LLM request configuration."""
    prompt: str
    system_prompt: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    stream: bool = False
    stop: list[str] | None = None
    tools: list[dict[str, Any]] | None = None


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
    """Unified client for multiple LLM providers."""

    # Provider API endpoints (using NewAPI as unified gateway)
    PROVIDER_ENDPOINTS = {
        LLMProvider.DEEPSEEK: "https://api.deepseek.com/v1/chat/completions",
        LLMProvider.GLM: "https://api.glm.ai/v1/chat/completions",
        LLMProvider.KIMI: "https://api.kimi.ai/v1/chat/completions",
        LLMProvider.GEMINI: "https://api.gemini.com/v1/chat/completions",
        LLMProvider.MINIMAX: "https://api.minimax.com/v1/chat/completions"
    }

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize LLM client."""
        self.config = config or {}
        self.router = get_router()
        self._session: aiohttp.ClientSession | None = None
        self._provider_configs = self._load_provider_configs()

    async def __aenter__(self) -> "LLMClient":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def initialize(self) -> None:
        """Initialize client resources."""
        if self._session is None:
            self._session = aiohttp.ClientSession()

    async def close(self) -> None:
        """Close client resources."""
        if self._session:
            await self._session.close()
            self._session = None

    def _load_provider_configs(self) -> dict[LLMProvider, dict[str, Any]]:
        """Load provider configurations."""
        config = get_config()
        base_config = {
            "api_key": config.llm.api_key,
            "api_base_url": config.llm.api_base_url,
            "timeout": 30,
            "max_retries": 3
        }

        return {
            LLMProvider.DEEPSEEK: {**base_config},
            LLMProvider.GLM: {**base_config},
            LLMProvider.KIMI: {**base_config},
            LLMProvider.GEMINI: {**base_config},
            LLMProvider.MINIMAX: {**base_config}
        }

    async def generate(self, request: LLMRequest,
                      task_type: TaskType | str | None = None,
                      model_name: str | None = None) -> LLMResponse | AsyncGenerator[str, None]:
        """
        Generate text using appropriate LLM.

        Args:
            request: LLM request configuration
            task_type: Optional task type for model selection
            model_name: Optional specific model name to use

        Returns:
            LLMResponse or async generator for streaming
        """
        # Select model
        if model_name:
            model_config = self.router.get_model_by_name(model_name)
            if not model_config:
                raise LLMError(f"Unknown model: {model_name}")
        elif task_type:
            model_config = self.router.get_model_for_task(task_type)
        else:
            # Auto-detect based on prompt
            model_config = self.router.get_recommendation(request.prompt)

        # Prepare request
        payload = self._prepare_payload(request, model_config)

        # Make API call
        try:
            if request.stream:
                return self._generate_stream(payload, model_config)
            else:
                return await self._generate_completion(payload, model_config)
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise LLMError(f"LLM generation failed: {e}") from e

    def _prepare_payload(self, request: LLMRequest,
                        model_config: ModelRouting) -> dict[str, Any]:
        """Prepare API payload."""
        messages = []

        # Add system prompt if provided
        if request.system_prompt:
            messages.append({
                "role": "system",
                "content": request.system_prompt
            })

        # Add user prompt
        messages.append({
            "role": "user",
            "content": request.prompt
        })

        payload = {
            "model": model_config.model_name,
            "messages": messages,
            "max_tokens": request.max_tokens or model_config.max_tokens,
            "temperature": request.temperature or model_config.temperature,
            "stream": request.stream
        }

        # Optional parameters
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.stop:
            payload["stop"] = request.stop
        if request.tools:
            payload["tools"] = request.tools

        return payload

    async def _generate_completion(self, payload: dict[str, Any],
                                  model_config: ModelRouting) -> LLMResponse:
        """Generate completion (non-streaming)."""
        provider = LLMProvider(model_config.provider)
        endpoint = self._get_endpoint(provider)

        headers = self._get_headers(provider)

        # 确保 session 已初始化
        if self._session is None:
            await self.initialize()
        assert self._session is not None  # noqa: S101

        async with self._session.post(endpoint, json=payload, headers=headers) as response:
            if response.status != 200:
                error_text = await response.text()
                raise LLMError(f"API error {response.status}: {error_text}")

            data = await response.json()

            # Extract response
            choice = data["choices"][0]
            message = choice["message"]

            return LLMResponse(
                content=message.get("content", ""),
                model=data["model"],
                usage=data.get("usage", {}),
                finish_reason=choice.get("finish_reason"),
                tool_calls=message.get("tool_calls")
            )

    async def _generate_stream(self, payload: dict[str, Any],
                              model_config: ModelRouting) -> AsyncGenerator[str, None]:
        """Generate streaming response."""
        provider = LLMProvider(model_config.provider)
        endpoint = self._get_endpoint(provider)
        headers = self._get_headers(provider)

        # 确保 session 已初始化
        if self._session is None:
            await self.initialize()
        assert self._session is not None  # noqa: S101

        async with self._session.post(endpoint, json=payload, headers=headers) as response:
            if response.status != 200:
                error_text = await response.text()
                raise LLMError(f"API error {response.status}: {error_text}")

            async for line in response.content:
                if line:
                    line_text = line.decode('utf-8').strip()
                    if line_text.startswith("data: "):
                        data = line_text[6:]
                        if data == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data)
                            choice = chunk["choices"][0]
                            delta = choice.get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse chunk: {data}")

    def _get_endpoint(self, provider: LLMProvider) -> str:
        """Get API endpoint for provider."""
        # Use config override if available
        config = self._provider_configs[provider]
        if config.get("api_base_url"):
            return f"{config['api_base_url']}/chat/completions"

        # Fallback to default endpoints
        return self.PROVIDER_ENDPOINTS[provider]

    def _get_headers(self, provider: LLMProvider) -> dict[str, str]:
        """Get headers for API request."""
        config = self._provider_configs[provider]
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Aegis-Trader/0.1.0"
        }

        # Add API key if available
        api_key = config.get("api_key")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        return headers

    async def health_check(self, provider: LLMProvider | None = None) -> bool:
        """
        Check health of LLM provider(s).

        Args:
            provider: Optional specific provider to check

        Returns:
            True if healthy, False otherwise
        """
        providers_to_check = [provider] if provider else list(LLMProvider)

        for prov in providers_to_check:
            try:
                endpoint = self._get_endpoint(prov)
                headers = self._get_headers(prov)

                # Simple health check request
                health_payload = {
                    "model": "test",
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1
                }

                # 确保 session 已初始化
                if self._session is None:
                    await self.initialize()
                assert self._session is not None  # noqa: S101

                async with self._session.post(endpoint, json=health_payload,
                                            headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        logger.info(f"Provider {prov} health check passed")
                    else:
                        logger.warning(f"Provider {prov} health check failed: {response.status}")
                        return False

            except Exception as e:
                logger.warning(f"Provider {prov} health check error: {e}")
                return False

        return True


# Global client instance
_client: LLMClient | None = None


def get_client() -> LLMClient:
    """Get the global LLM client instance."""
    global _client
    if _client is None:
        config = get_config()
        _client = LLMClient(config.model_dump())
    return _client


async def generate(prompt: str,
                  system_prompt: str | None = None,
                  task_type: TaskType | str | None = None,
                  model_name: str | None = None,
                  **kwargs: Any) -> str:
    """
    Convenience function for simple text generation.

    Args:
        prompt: User prompt
        system_prompt: Optional system prompt
        task_type: Optional task type for model selection
        model_name: Optional specific model name
        **kwargs: Additional LLMRequest parameters

    Returns:
        Generated text
    """
    request = LLMRequest(prompt=prompt, system_prompt=system_prompt, **kwargs)
    client = get_client()

    async with client:
        response = await client.generate(request, task_type, model_name)
        assert isinstance(response, LLMResponse)  # noqa: S101
        return response.content


async def generate_stream(prompt: str,
                         system_prompt: str | None = None,
                         task_type: TaskType | str | None = None,
                         model_name: str | None = None,
                         **kwargs: Any) -> AsyncGenerator[str, None]:
    """
    Convenience function for streaming text generation.

    Args:
        prompt: User prompt
        system_prompt: Optional system prompt
        task_type: Optional task type for model selection
        model_name: Optional specific model name
        **kwargs: Additional LLMRequest parameters

    Yields:
        Generated text chunks
    """
    request = LLMRequest(prompt=prompt, system_prompt=system_prompt,
                        stream=True, **kwargs)
    client = get_client()

    async with client:
        stream = client.generate(request, task_type, model_name)
        assert isinstance(stream, AsyncGenerator)  # noqa: S101
        async for chunk in stream:
            yield chunk

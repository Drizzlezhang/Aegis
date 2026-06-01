"""Tests for single-provider LLM client (OpenAI-compatible API)."""

from unittest.mock import MagicMock, patch

import pytest

from src.llm.client import LLMClient, LLMError, LLMRequest, LLMResponse


class TestLLMClient:
    """Tests for the single-provider LLMClient."""

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful completion generation."""
        client = LLMClient(base_url="https://api.example.com/v1", api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello"}, "finish_reason": "stop"}],
            "model": "gpt-4o-mini",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

        with patch.object(client._client, "post", return_value=mock_response):
            req = LLMRequest(prompt="Hi", model="gpt-4o-mini")
            resp = await client.generate(req)

        assert isinstance(resp, LLMResponse)
        assert resp.content == "Hello"
        assert resp.model == "gpt-4o-mini"
        assert resp.finish_reason == "stop"
        await client.close()

    @pytest.mark.asyncio
    async def test_generate_stream(self):
        """Test streaming completion generation."""
        client = LLMClient(base_url="https://api.example.com/v1", api_key="test-key")

        chunks = []

        class FakeStreamResponse:
            status_code = 200

            async def aiter_lines(self):
                yield 'data: {"choices":[{"delta":{"content":"Hello"}}]}'
                yield 'data: {"choices":[{"delta":{"content":" world"}}]}'
                yield "data: [DONE]"

            async def aread(self):
                return b""

        class FakeStreamCtx:
            async def __aenter__(self):
                return FakeStreamResponse()

            async def __aexit__(self, *args):
                pass

        with patch.object(client._client, "stream", return_value=FakeStreamCtx()):
            req = LLMRequest(prompt="Hi", model="gpt-4o-mini")
            async for chunk in client.generate_stream(req):
                chunks.append(chunk)

        assert "".join(chunks) == "Hello world"
        await client.close()

    @pytest.mark.asyncio
    async def test_generate_api_error(self):
        """Test API error handling."""
        client = LLMClient(base_url="https://api.example.com/v1", api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch.object(client._client, "post", return_value=mock_response):
            req = LLMRequest(prompt="Hi")
            with pytest.raises(LLMError, match="API error 401"):
                await client.generate(req)

        await client.close()

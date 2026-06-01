"""LLMClient error handling tests.

Updated sprint15-hotfix-v0.15.2: LLMClient now requires base_url + api_key,
uses httpx.AsyncClient. No built-in retry — errors propagate directly.
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.llm.client import LLMClient, LLMError


@pytest.fixture
def client():
    return LLMClient(base_url="https://api.test.com/v1", api_key="sk-test")


@pytest.mark.asyncio
async def test_http_error_raises_llm_error(client):
    """HTTP errors raise LLMError directly (no retry)."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch.object(client._client, "post", return_value=mock_response):
        with pytest.raises(LLMError, match="API error 500"):
            await client.generate(MagicMock(messages=[{"role": "user", "content": "hi"}], model="test"))


@pytest.mark.asyncio
async def test_client_error_raises_llm_error(client):
    """400 client errors raise LLMError directly."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 400
    mock_response.text = "Bad Request"

    with patch.object(client._client, "post", return_value=mock_response):
        with pytest.raises(LLMError, match="API error 400"):
            await client.generate(MagicMock(messages=[{"role": "user", "content": "hi"}], model="test"))


@pytest.mark.asyncio
async def test_rate_limit_raises_llm_error(client):
    """429 rate limit raises LLMError directly."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 429
    mock_response.text = "Rate limited"

    with patch.object(client._client, "post", return_value=mock_response):
        with pytest.raises(LLMError, match="API error 429"):
            await client.generate(MagicMock(messages=[{"role": "user", "content": "hi"}], model="test"))

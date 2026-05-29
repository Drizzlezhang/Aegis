"""LLMClient 重试逻辑测试。"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.llm.client import LLMClient, LLMError


def _mock_response(status=200, headers=None, json_data=None, text_data=""):
    """Create a mock aiohttp response."""
    resp = AsyncMock()
    resp.status = status
    resp.headers = headers or {}
    resp.text = AsyncMock(return_value=text_data)
    resp.json = AsyncMock(return_value=json_data or {})
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp


@pytest.fixture
def client():
    return LLMClient()


@pytest.mark.asyncio
async def test_retry_on_429(client):
    """429 rate limit → 重试。"""
    mock_session = AsyncMock()
    client._session = mock_session

    resp_429 = _mock_response(status=429, headers={"Retry-After": "0.01"})
    _mock_response(status=200, json_data={
        "choices": [{"message": {"content": "ok"}}],
        "model": "test",
        "usage": {},
    })

    mock_session.post = MagicMock(return_value=resp_429)

    # After 3 retries all 429, should raise
    with patch("asyncio.sleep", new_callable=AsyncMock):
        # All 429
        mock_session.post = MagicMock(side_effect=[resp_429, resp_429, resp_429])
        with pytest.raises(LLMError, match="retries exhausted"):
            await client._generate_completion({"messages": []}, MagicMock(provider="deepseek", model_name="test"))


@pytest.mark.asyncio
async def test_retry_on_500(client):
    """500 服务端错误 → 退避重试。"""
    client._session = AsyncMock()

    resp_500 = _mock_response(status=500, text_data="Internal Server Error")
    resp_200 = _mock_response(status=200, json_data={
        "choices": [{"message": {"content": "ok"}}],
        "model": "test",
        "usage": {},
    })

    with patch("asyncio.sleep", new_callable=AsyncMock):
        client._session.post = MagicMock(side_effect=[resp_500, resp_200])
        result = await client._generate_completion({"messages": []}, MagicMock(provider="deepseek", model_name="test"))
        assert result.content == "ok"


@pytest.mark.asyncio
async def test_no_retry_on_400(client):
    """400 客户端错误 → 不重试，直接报错。"""
    client._session = AsyncMock()

    resp_400 = _mock_response(status=400, text_data="Bad Request")

    client._session.post = MagicMock(return_value=resp_400)
    with pytest.raises(LLMError, match="API error 400"):
        await client._generate_completion({"messages": []}, MagicMock(provider="deepseek", model_name="test"))


@pytest.mark.asyncio
async def test_retry_exhausted(client):
    """3 次都失败 → 抛 RuntimeError。"""
    client._session = AsyncMock()

    resp_500 = _mock_response(status=500, text_data="error")

    with patch("asyncio.sleep", new_callable=AsyncMock):
        client._session.post = MagicMock(return_value=resp_500)
        with pytest.raises(LLMError, match="retries exhausted"):
            await client._generate_completion({"messages": []}, MagicMock(provider="deepseek", model_name="test"))


@pytest.mark.asyncio
async def test_success_on_second_attempt(client):
    """第一次失败第二次成功 → 返回结果。"""
    client._session = AsyncMock()

    resp_500 = _mock_response(status=500, text_data="error")
    resp_200 = _mock_response(status=200, json_data={
        "choices": [{"message": {"content": "success"}}],
        "model": "test",
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    })

    with patch("asyncio.sleep", new_callable=AsyncMock):
        client._session.post = MagicMock(side_effect=[resp_500, resp_200])
        result = await client._generate_completion({"messages": []}, MagicMock(provider="deepseek", model_name="test"))
        assert result.content == "success"

"""LLMGateway 指标测试。"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.llm.client import LLMError, LLMRequest, LLMResponse
from src.llm.gateway import LLMGateway, LLMMetrics


@pytest.fixture
def mock_client():
    """Create mock LLMClient."""
    client = MagicMock()
    client.generate = AsyncMock()
    return client


@pytest.fixture
def gateway(mock_client):
    """Create LLMGateway with mock client."""
    return LLMGateway(client=mock_client)


@pytest.mark.asyncio
async def test_gateway_records_success(gateway, mock_client):
    """成功请求记录 total_requests + requests_by_model。"""
    mock_client.generate.return_value = LLMResponse(
        content="ok", model="deepseek-v3.2", usage={"total_tokens": 15}
    )

    request = LLMRequest(prompt="test")
    response = await gateway.generate(request, model_name="deepseek-v3.2")

    assert response.content == "ok"
    assert gateway.metrics.total_requests == 1
    assert gateway.metrics.total_errors == 0
    assert gateway.metrics.requests_by_model["deepseek-v3.2"] == 1


@pytest.mark.asyncio
async def test_gateway_records_error(gateway, mock_client):
    """失败请求记录 total_errors + errors_by_model。"""
    mock_client.generate.side_effect = LLMError("API down")

    request = LLMRequest(prompt="test")
    with pytest.raises(LLMError):
        await gateway.generate(request, model_name="deepseek-v3.2")

    assert gateway.metrics.total_requests == 1
    assert gateway.metrics.total_errors == 1
    assert gateway.metrics.errors_by_model["deepseek-v3.2"] == 1


@pytest.mark.asyncio
async def test_gateway_records_latency(gateway, mock_client):
    """延迟被记录到 avg_latency_ms。"""
    mock_client.generate.return_value = LLMResponse(
        content="ok", model="glm5.1", usage={}
    )

    request = LLMRequest(prompt="test")
    await gateway.generate(request, model_name="glm5.1")

    assert gateway.metrics.avg_latency_ms >= 0


@pytest.mark.asyncio
async def test_gateway_records_tokens(gateway, mock_client):
    """token 用量计入 total_tokens。"""
    mock_client.generate.return_value = LLMResponse(
        content="ok", model="kimi", usage={"total_tokens": 42}
    )

    request = LLMRequest(prompt="test")
    await gateway.generate(request, model_name="kimi")

    assert gateway.metrics.total_tokens == 42


@pytest.mark.asyncio
async def test_gateway_multiple_requests_aggregate(gateway, mock_client):
    """多次请求指标累加。"""
    mock_client.generate.side_effect = [
        LLMResponse(content="ok", model="m1", usage={"total_tokens": 10}),
        LLMResponse(content="ok", model="m1", usage={"total_tokens": 20}),
        LLMResponse(content="ok", model="m2", usage={"total_tokens": 5}),
    ]

    for _ in range(3):
        await gateway.generate(LLMRequest(prompt="test"))

    assert gateway.metrics.total_requests == 3
    assert gateway.metrics.total_tokens == 35


@pytest.mark.asyncio
async def test_gateway_error_does_not_block(gateway, mock_client):
    """错误后Gateway继续可用。"""
    mock_client.generate.side_effect = [
        LLMError("fail"),
        LLMResponse(content="ok", model="m1", usage={}),
    ]

    with pytest.raises(LLMError):
        await gateway.generate(LLMRequest(prompt="test"))

    response = await gateway.generate(LLMRequest(prompt="test"))
    assert response.content == "ok"
    assert gateway.metrics.total_errors == 1
    assert gateway.metrics.total_requests == 2

"""Tests for LLM router and client."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.llm.client import LLMClient, LLMProvider, LLMRequest, LLMResponse
from src.llm.router import LLMRouter, ModelRouting, TaskType


class TestLLMRouter:
    """Tests for LLM router."""

    def test_task_type_enum(self):
        """Test TaskType enum values."""
        assert TaskType.PLAN.value == "plan"
        assert TaskType.CODE.value == "code"
        assert TaskType.REVIEW.value == "review"
        assert TaskType.ANALYSIS.value == "analysis"
        assert TaskType.REPORT.value == "report"
        assert TaskType.QUERY.value == "query"

    def test_get_model_for_task_plan(self):
        """Test model selection for planning tasks."""
        router = LLMRouter()
        model = router.get_model_for_task(TaskType.PLAN)

        assert model.model_name == "deepseek-v3.2"
        assert model.provider == "deepseek"
        assert model.max_tokens == 32768

    def test_get_model_for_task_code(self):
        """Test model selection for coding tasks."""
        router = LLMRouter()
        model = router.get_model_for_task(TaskType.CODE)

        assert model.model_name == "glm5.1"
        assert model.provider == "glm"

    def test_get_model_for_task_review(self):
        """Test model selection for review tasks."""
        router = LLMRouter()
        model = router.get_model_for_task(TaskType.REVIEW)

        assert model.model_name == "deepseek-v3.2"

    def test_get_model_for_task_string(self):
        """Test model selection with string task type."""
        router = LLMRouter()
        model = router.get_model_for_task("plan")

        assert model.model_name == "deepseek-v3.2"

    def test_get_model_for_task_unknown_string(self):
        """Test model selection with unknown string task type."""
        router = LLMRouter()
        model = router.get_model_for_task("unknown_task")

        assert model.model_name == "deepseek-v3.2"

    def test_user_override(self):
        """Test user override configuration."""
        config = {
            "model_overrides": {
                "plan": "deepseek-v3.2",
                "code": "deepseek-v3.2"  # 统一使用 deepseek-v3.2
            }
        }
        router = LLMRouter(config)

        plan_model = router.get_model_for_task(TaskType.PLAN)
        code_model = router.get_model_for_task(TaskType.CODE)

        assert plan_model.model_name == "deepseek-v3.2"
        assert code_model.model_name == "deepseek-v3.2"

    def test_user_override_unknown_model(self):
        """Test user override with unknown model."""
        config = {
            "model_overrides": {
                "plan": "unknown_model"
            }
        }
        router = LLMRouter(config)

        # Should fall back to default (deepseek-v3.2)
        model = router.get_model_for_task(TaskType.PLAN)
        assert model.model_name == "deepseek-v3.2"

    def test_long_context_switching(self):
        """Test model switching for long context."""
        router = LLMRouter()

        model = router.get_model_for_task(TaskType.CODE, context_length=35000)
        assert model.model_name == "gemini-pro"

        model = router.get_model_for_task(TaskType.CODE, context_length=10000)
        assert model.model_name == "glm5.1"

    def test_get_model_by_name(self):
        """Test getting model by name."""
        router = LLMRouter()
        model = router.get_model_by_name("glm5.1")

        assert model is not None
        assert model.model_name == "glm5.1"

    def test_get_model_by_name_unknown(self):
        """Test getting unknown model by name."""
        router = LLMRouter()
        model = router.get_model_by_name("unknown_model")

        assert model is None

    def test_list_available_models(self):
        """Test listing available models."""
        router = LLMRouter()
        models = router.list_available_models()

        assert "glm5.1" in models
        assert "deepseek-v3.2" in models
        assert "kimi" in models
        assert "gemini-pro" in models
        assert "minimax-2.7" in models

    def test_get_models_by_provider(self):
        """Test getting models by provider."""
        router = LLMRouter()
        models = router.get_models_by_provider("deepseek")

        assert len(models) >= 1
        assert all(model.provider == "deepseek" for model in models)

    def test_estimate_cost(self):
        """Test cost estimation."""
        router = LLMRouter()
        cost = router.estimate_cost("deepseek-v3.2", 1000, 500)

        assert cost is not None
        assert cost > 0

    def test_estimate_cost_unknown_model(self):
        """Test cost estimation for unknown model."""
        router = LLMRouter()
        cost = router.estimate_cost("unknown_model", 1000, 500)

        assert cost is None

    def test_get_recommendation_keywords(self):
        """Test model recommendation based on keywords."""
        router = LLMRouter()

        model = router.get_recommendation("Design a new system architecture")
        assert model.model_name == "deepseek-v3.2"

        model = router.get_recommendation("Write a Python function to calculate moving average")
        assert model.model_name == "glm5.1"

        model = router.get_recommendation("Review this for potential bugs")
        assert model.model_name == "deepseek-v3.2"

        model = router.get_recommendation("Analyze market trends and patterns")
        assert model.model_name == "deepseek-v3.2"

        model = router.get_recommendation("Generate a summary report of trading activities")
        assert model.model_name == "gemini-pro"

        model = router.get_recommendation("Query the current price of QQQ")
        assert model.model_name == "minimax-2.7"

        model = router.get_recommendation("Some random text")
        assert model.model_name == "deepseek-v3.2"


class TestLLMClient:
    """Tests for LLM client."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock aiohttp session."""
        with patch('aiohttp.ClientSession') as mock_session_cls:
            mock_session = MagicMock()  # 使用 MagicMock 而不是 AsyncMock
            mock_session_cls.return_value = mock_session
            yield mock_session

    @pytest.fixture
    def client(self, mock_session):
        """Create LLM client with mocked session."""
        client = LLMClient()
        client._session = mock_session
        return client

    def _create_mock_context(self, mock_response):
        """Create a proper async context manager mock."""
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        return mock_context

    def _create_post_mock(self, mock_context):
        """Create proper post mock that returns async context manager."""
        # 返回一个 MagicMock，其 return_value 是 async context manager
        post_mock = MagicMock(return_value=mock_context)
        return post_mock

    @pytest.mark.asyncio
    async def test_generate_completion(self, client, mock_session):
        """Test non-streaming text generation."""
        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "This is the generated text.",
                    "role": "assistant"
                },
                "finish_reason": "stop"
            }],
            "model": "deepseek-v3.2",
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
        }

        mock_context = self._create_mock_context(mock_response)
        mock_session.post = self._create_post_mock(mock_context)

        # Create request
        request = LLMRequest(
            prompt="Write a function to calculate fibonacci",
            system_prompt="You are a helpful coding assistant"
        )

        # Generate
        response = await client.generate(request, task_type=TaskType.CODE)

        assert isinstance(response, LLMResponse)
        assert response.content == "This is the generated text."
        assert response.model == "deepseek-v3.2"
        assert response.usage["total_tokens"] == 15

    @pytest.mark.asyncio
    async def test_generate_stream(self, client, mock_session):
        """Test streaming text generation."""
        # Mock streaming response
        mock_response = AsyncMock()
        mock_response.status = 200

        # Simulate streaming chunks
        chunks = [
            b'data: {"choices": [{"delta": {"content": "Hello"}}]}\n',
            b'data: {"choices": [{"delta": {"content": " world"}}]}\n',
            b'data: [DONE]\n'
        ]

        # 清理之前的调试输出
        # Create async iterable for response.content
        async def content_iterable():
            for chunk in chunks:
                yield chunk

        mock_response.content = content_iterable()

        mock_context = self._create_mock_context(mock_response)
        mock_session.post = self._create_post_mock(mock_context)

        # Create request
        request = LLMRequest(
            prompt="Say hello",
            stream=True
        )

        # 清理之前的调试输出
        # Generate stream
        stream_generator = await client.generate(request, task_type=TaskType.QUERY)
        chunks_collected = []
        async for chunk in stream_generator:
            chunks_collected.append(chunk)

        assert chunks_collected == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_generate_with_specific_model(self, client, mock_session):
        """Test generation with specific model name."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test"}}],
            "model": "glm5.1",
            "usage": {}
        }

        mock_context = self._create_mock_context(mock_response)
        mock_session.post = self._create_post_mock(mock_context)

        request = LLMRequest(prompt="Test")
        response = await client.generate(request, model_name="glm5.1")

        assert response.model == "glm5.1"

    @pytest.mark.asyncio
    async def test_generate_api_error(self, client, mock_session):
        """Test handling of API errors."""
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text.return_value = "Internal server error"

        mock_context = self._create_mock_context(mock_response)
        mock_session.post = self._create_post_mock(mock_context)

        request = LLMRequest(prompt="Test")

        with pytest.raises(Exception) as exc_info:
            await client.generate(request, task_type=TaskType.CODE)

        assert "retries exhausted" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_health_check_success(self, client, mock_session):
        """Test successful health check."""
        mock_response = AsyncMock()
        mock_response.status = 200

        mock_context = self._create_mock_context(mock_response)
        mock_session.post = self._create_post_mock(mock_context)

        result = await client.health_check(LLMProvider.DEEPSEEK)

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client, mock_session):
        """Test failed health check."""
        mock_response = AsyncMock()
        mock_response.status = 503

        mock_context = self._create_mock_context(mock_response)
        mock_session.post = self._create_post_mock(mock_context)

        result = await client.health_check(LLMProvider.DEEPSEEK)

        assert result is False

    def test_prepare_payload(self, client):
        """Test payload preparation."""
        request = LLMRequest(
            prompt="User prompt",
            system_prompt="System instructions",
            max_tokens=1000,
            temperature=0.7,
            top_p=0.9,
            stop=["\n", "STOP"],
            tools=[{"type": "function", "function": {"name": "test"}}]
        )

        model_config = ModelRouting(
            model_name="test-model",
            provider="test",
            max_tokens=2000,
            temperature=0.5,
            description="Test model"
        )

        payload = client._prepare_payload(request, model_config)

        assert payload["model"] == "test-model"
        assert payload["max_tokens"] == 1000  # Request overrides model default
        assert payload["temperature"] == 0.7
        assert payload["top_p"] == 0.9
        assert payload["stop"] == ["\n", "STOP"]
        assert payload["tools"] == [{"type": "function", "function": {"name": "test"}}]

        # Check messages structure
        messages = payload["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "System instructions"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "User prompt"

    def test_prepare_payload_no_system_prompt(self, client):
        """Test payload preparation without system prompt."""
        request = LLMRequest(prompt="User prompt")
        model_config = ModelRouting(
            model_name="test-model",
            provider="test",
            max_tokens=2000,
            temperature=0.5,
            description="Test model"
        )

        payload = client._prepare_payload(request, model_config)

        messages = payload["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "User prompt"

    def test_get_endpoint_default(self, client):
        """Test getting default endpoint."""
        endpoint = client._get_endpoint(LLMProvider.DEEPSEEK)

        assert "deepseek.com" in endpoint

    def test_get_endpoint_override(self, client):
        """Test getting endpoint with override."""
        client._provider_configs[LLMProvider.DEEPSEEK]["api_base_url"] = "https://custom.api.com"

        endpoint = client._get_endpoint(LLMProvider.DEEPSEEK)

        assert "custom.api.com" in endpoint
        assert endpoint == "https://custom.api.com/chat/completions"

    def test_get_headers_with_api_key(self, client):
        """Test getting headers with API key."""
        client._provider_configs[LLMProvider.DEEPSEEK]["api_key"] = "test-api-key"

        headers = client._get_headers(LLMProvider.DEEPSEEK)

        assert headers["Authorization"] == "Bearer test-api-key"
        assert headers["Content-Type"] == "application/json"

    def test_get_headers_no_api_key(self, client):
        """Test getting headers without API key."""
        client._provider_configs[LLMProvider.DEEPSEEK]["api_key"] = None

        headers = client._get_headers(LLMProvider.DEEPSEEK)

        assert "Authorization" not in headers
        assert headers["Content-Type"] == "application/json"

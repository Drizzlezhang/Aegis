"""LLMRouter 配置化路由测试。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import get_config
from src.llm.router import LLMRouter, TaskType


@pytest.fixture
def router():
    return LLMRouter()


def test_default_routing_uses_config(router):
    """路由表从 LLMConfig 读取模型名。"""
    config = get_config()
    assert router.get_model_for_task(TaskType.REASONING).model_name == config.llm.reasoning_model
    assert router.get_model_for_task(TaskType.QUERY).model_name == config.llm.quick_model


def test_code_task_routes_to_code_model(router):
    """CODE/DEBUG/REFACTOR → code_model。"""
    config = get_config()
    code_model = config.llm.code_model
    assert router.get_model_for_task(TaskType.CODE).model_name == code_model
    assert router.get_model_for_task(TaskType.DEBUG).model_name == code_model
    assert router.get_model_for_task(TaskType.REFACTOR).model_name == code_model


def test_quick_task_routes_to_quick_model(router):
    """QUERY/CONFIG/STATUS → quick_model。"""
    config = get_config()
    quick_model = config.llm.quick_model
    assert router.get_model_for_task(TaskType.QUERY).model_name == quick_model
    assert router.get_model_for_task(TaskType.CONFIG).model_name == quick_model
    assert router.get_model_for_task(TaskType.STATUS).model_name == quick_model


def test_long_context_switch(router):
    """context_length > 32000 → long_context_model。"""
    config = get_config()
    long_ctx = config.llm.long_context_model
    result = router.get_model_for_task(TaskType.REPORT, context_length=50000)
    assert result.model_name == long_ctx


def test_model_override():
    """用户自定义 override 优先。"""
    router = LLMRouter(config={"model_overrides": {"query": "deepseek-v3.2"}})
    assert router.get_model_for_task(TaskType.QUERY).model_name == "deepseek-v3.2"


def test_debate_routing(router):
    """DEBATE_QUICK → quick, DEBATE_DEEP → reasoning。"""
    config = get_config()
    assert router.get_model_for_task(TaskType.DEBATE_QUICK).model_name == config.llm.quick_model
    assert router.get_model_for_task(TaskType.DEBATE_DEEP).model_name == config.llm.reasoning_model

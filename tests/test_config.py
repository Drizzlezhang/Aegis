"""Config 字段完整性测试。"""

import sys
import os
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import PositionConfig, LLMConfig, ProviderCredential, get_config


def test_position_config_has_all_fields():
    """PositionConfig 包含 profit_target_pct 和 dte_warning_days。"""
    pc = PositionConfig()
    assert hasattr(pc, "profit_target_pct")
    assert hasattr(pc, "dte_warning_days")
    assert pc.profit_target_pct == 1.0
    assert pc.dte_warning_days == 30


def test_llm_config_provider_credentials():
    """LLMConfig 支持 providers dict 和 ProviderCredential。"""
    lc = LLMConfig()
    assert isinstance(lc.providers, dict)
    assert lc.max_retries == 3
    assert lc.retry_base_delay == 1.0

    lc_with_cred = LLMConfig(providers={"deepseek": ProviderCredential(api_key="sk-test")})
    assert lc_with_cred.providers["deepseek"].api_key == "sk-test"


def test_env_var_override():
    """AEGIS_LLM__QUICK_MODEL 环境变量生效。"""
    os.environ["AEGIS_LLM__QUICK_MODEL"] = "custom-model"
    try:
        from src.config import Config
        c = Config()
        assert c.llm.quick_model == "custom-model"
    finally:
        del os.environ["AEGIS_LLM__QUICK_MODEL"]

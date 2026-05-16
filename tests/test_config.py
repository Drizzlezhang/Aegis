"""Config 字段完整性测试。"""

import sys
import os
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import (
    Config,
    ConfigProfile,
    LLMConfig,
    PositionConfig,
    ProviderCredential,
    get_config,
    reload_config,
)


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
        c = Config()
        assert c.llm.quick_model == "custom-model"
    finally:
        del os.environ["AEGIS_LLM__QUICK_MODEL"]


def test_config_profile_production():
    """PRODUCTION profile 差异化参数正确。"""
    c = Config(profile=ConfigProfile.PRODUCTION)
    assert c.llm.max_retries == 5
    assert c.llm.retry_base_delay == 2.0
    assert c.data_source.circuit_breaker_threshold == 5
    assert c.llm.enable_request_logging is True


def test_config_profile_development():
    """DEVELOPMENT profile 默认参数。"""
    c = Config(profile=ConfigProfile.DEVELOPMENT)
    assert c.llm.max_retries == 3
    assert c.llm.retry_base_delay == 1.0
    assert c.data_source.circuit_breaker_threshold == 3
    assert c.llm.enable_request_logging is False


def test_reload_config():
    """reload_config 重新加载环境变量。"""
    import src.config as cfg_mod
    cfg_mod._config = None
    os.environ["AEGIS_LLM__QUICK_MODEL"] = "reloaded-model"
    try:
        c = reload_config()
        assert c.llm.quick_model == "reloaded-model"
    finally:
        del os.environ["AEGIS_LLM__QUICK_MODEL"]
        cfg_mod._config = None

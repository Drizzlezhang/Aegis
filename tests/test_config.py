"""Config 字段完整性测试。"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import (
    Config,
    ConfigProfile,
    LLMConfig,
    PhaseConfig,
    PositionConfig,
    ProviderCredential,
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


class TestPhaseConfigValidation:
    """Tests for PhaseConfig model validation."""

    def test_default_weights_pass_validation(self):
        """默认权重 sum=1.0 → 构造成功."""
        config = PhaseConfig()
        assert config is not None

    def test_weights_sum_below_threshold_raises(self):
        """权重总和 < 0.99 → ValidationError."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="weights must sum to 1.0"):
            PhaseConfig(weights={"trend_momentum": 0.5, "velocity": 0.1})

    def test_weights_sum_above_threshold_raises(self):
        """权重总和 > 1.01 → ValidationError."""
        from pydantic import ValidationError
        weights = {"trend_momentum": 0.50, "velocity": 0.30, "acceleration": 0.30}
        with pytest.raises(ValidationError):
            PhaseConfig(weights=weights)

    def test_weights_within_tolerance_pass(self):
        """权重总和 = 0.995 (在 ±0.01 内) → 通过."""
        weights = {
            "trend_momentum": 0.195, "velocity": 0.15, "acceleration": 0.12,
            "volume": 0.18, "mean_reversion": 0.15, "macro": 0.10, "valuation": 0.10,
        }
        config = PhaseConfig(weights=weights)
        assert config is not None

    def test_sensitivity_positive_constraint(self):
        """sensitivity 必须 > 0."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PhaseConfig(velocity_sensitivity=-1.0)

    def test_custom_sensitivity_values(self):
        """自定义 sensitivity 值可正确设置."""
        config = PhaseConfig(velocity_sensitivity=3000.0, acceleration_sensitivity=800.0)
        assert config.velocity_sensitivity == 3000.0
        assert config.acceleration_sensitivity == 800.0

    def test_cooldown_range_constraint(self):
        """cooldown 超出 [1,20] 范围 → 报错."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PhaseConfig(phase_transition_cooldown_bars=0)
        with pytest.raises(ValidationError):
            PhaseConfig(phase_transition_cooldown_bars=25)

    def test_default_cooldown_value(self):
        """默认 cooldown = 3."""
        config = PhaseConfig()
        assert config.phase_transition_cooldown_bars == 3

    def test_adx_period_default(self):
        """默认 ADX period = 14."""
        config = PhaseConfig()
        assert config.adx_period == 14

    def test_rsi_period_default(self):
        """默认 RSI period = 14."""
        config = PhaseConfig()
        assert config.rsi_period == 14

    def test_validate_weights_deprecated(self):
        """validate_weights() 仍可用但发出 DeprecationWarning."""
        config = PhaseConfig()
        with pytest.warns(DeprecationWarning, match="validate_weights"):
            assert config.validate_weights() is True

"""Tests for config startup validation."""

import pytest

from src.config import Config, ConfigValidationError


class TestConfigValidation:
    def test_validation_warns_on_short_jwt_secret(self, monkeypatch):
        """Empty or short JWT secret produces a validation warning."""
        monkeypatch.setenv("AEGIS_AUTH__JWT_SECRET", "")
        config = Config()
        warnings = config.validation_warnings
        assert len(warnings) >= 1
        assert any("JWT_SECRET" in w for w in warnings)

    def test_validation_warns_on_missing_llm_key(self, monkeypatch):
        """Missing all LLM keys produces a validation warning."""
        monkeypatch.setenv("AEGIS_AUTH__JWT_SECRET", "a" * 16)
        monkeypatch.setenv("AEGIS_LLM__API_KEY", "")
        config = Config()
        warnings = config.validation_warnings
        assert any("LLM" in w for w in warnings)

    def test_is_production_ready_false_when_issues_exist(self, monkeypatch):
        """is_production_ready returns False when validation warnings exist."""
        monkeypatch.setenv("AEGIS_AUTH__JWT_SECRET", "")
        config = Config()
        assert config.is_production_ready is False

    def test_is_production_ready_true_when_no_issues(self, monkeypatch):
        """is_production_ready returns True when all secrets are set."""
        monkeypatch.setenv("AEGIS_AUTH__JWT_SECRET", "a" * 16)
        monkeypatch.setenv("AEGIS_LLM__API_KEY", "sk-test")
        config = Config()
        assert config.is_production_ready is True

    def test_strict_mode_raises_on_validation_failure(self, monkeypatch):
        """strict_validation=True raises ConfigValidationError on issues."""
        monkeypatch.setenv("AEGIS_AUTH__JWT_SECRET", "")
        monkeypatch.setenv("AEGIS_STRICT_VALIDATION", "true")
        with pytest.raises(ConfigValidationError):
            Config()

    def test_strict_mode_passes_when_no_issues(self, monkeypatch):
        """strict_validation=True does not raise when all secrets are set."""
        monkeypatch.setenv("AEGIS_AUTH__JWT_SECRET", "a" * 16)
        monkeypatch.setenv("AEGIS_LLM__API_KEY", "sk-test")
        monkeypatch.setenv("AEGIS_STRICT_VALIDATION", "true")
        config = Config()
        assert config.is_production_ready is True

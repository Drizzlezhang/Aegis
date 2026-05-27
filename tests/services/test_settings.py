"""Tests for SettingsService."""

import tempfile
from pathlib import Path

import pytest

from src.services.settings import SETTINGS_PATH, SettingsService, UserSettings


@pytest.fixture
def service(monkeypatch, tmp_path):
    """Create a SettingsService with a temp path."""
    temp_file = tmp_path / "settings.json"
    monkeypatch.setattr("src.services.settings.SETTINGS_PATH", temp_file)
    svc = SettingsService()
    return svc


class TestSettingsService:
    def test_get_current_defaults(self, service):
        """Default settings use built-in defaults."""
        settings = service.get_current()
        assert settings.confidence_threshold == 0.7
        assert settings.telegram.enabled is False
        assert settings.scheduler.enabled is True

    def test_update_partial(self, service):
        """Partial update only changes specified fields."""
        service.update({"confidence_threshold": 0.85})
        settings = service.get_current()
        assert settings.confidence_threshold == 0.85
        assert settings.telegram.enabled is False

    def test_update_nested(self, service):
        """Nested dict update merges correctly."""
        service.update({"telegram": {"enabled": True, "bot_token": "test123"}})
        settings = service.get_current()
        assert settings.telegram.enabled is True
        assert settings.telegram.bot_token == "test123"
        assert settings.telegram.chat_id == ""

    def test_persistence(self, service, monkeypatch, tmp_path):
        """Settings persist across service instances."""
        temp_file = tmp_path / "settings.json"
        monkeypatch.setattr("src.services.settings.SETTINGS_PATH", temp_file)

        service.update({"confidence_threshold": 0.9})

        svc2 = SettingsService()
        assert svc2.get_current().confidence_threshold == 0.9

    def test_apply_to_runtime_reschedules_job(self, service, monkeypatch):
        """apply_to_runtime calls scheduler.reschedule_job."""
        calls = []

        class MockScheduler:
            def reschedule_job(self, job_id, **kwargs):
                calls.append((job_id, kwargs))

        class MockAppState:
            scheduler = MockScheduler()
            notification_settings = None

        service.update({"scheduler": {"daily_run_time": "18:00"}})
        app_state = MockAppState()
        service.apply_to_runtime(app_state)

        assert len(calls) == 1
        assert calls[0][0] == "tracking_update"
        assert calls[0][1]["hour"] == 18
        assert calls[0][1]["minute"] == 0
        assert app_state.notification_settings is not None
        assert app_state.notification_settings["notify_on_high_confidence"] is True

"""Tests for alerting rules file watching (hot-reload via watchdog)."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from src.services.alerting import AlertEngine, AlertRule, load_rules_from_yaml
from src.services.event_bus import EventBus


class FakeNotifier:
    def __init__(self):
        self.messages: list[str] = []

    async def send_message(self, message: str, force: bool = False) -> bool:
        self.messages.append(message)
        return True


class TestAlertingFileWatch:
    """Tests for file watching and hot-reload."""

    @pytest.fixture
    def bus(self):
        return EventBus()

    @pytest.fixture
    def notifier(self):
        return FakeNotifier()

    def test_start_watching_noop_when_watchdog_missing(self, bus, notifier, monkeypatch):
        """start_watching is a no-op when watchdog is not installed."""
        import builtins

        _original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name.startswith("watchdog"):
                raise ImportError("No module named 'watchdog'")
            return _original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        rules = [AlertRule(name="test", event_type="PhaseEvent", condition=".confidence < 30")]
        engine = AlertEngine(bus, rules, notifier)
        # Should not raise
        engine.start_watching("config/alerting_rules.yaml")
        assert engine._observer is None

    def test_start_watching_noop_when_file_missing(self, bus, notifier, tmp_path):
        """start_watching is a no-op when the rules file does not exist."""
        rules = [AlertRule(name="test", event_type="PhaseEvent", condition=".confidence < 30")]
        engine = AlertEngine(bus, rules, notifier)
        nonexistent = tmp_path / "nonexistent.yaml"
        engine.start_watching(str(nonexistent))
        assert engine._observer is None

    def test_stop_watching_when_not_watching(self, bus, notifier):
        """stop_watching is safe to call when not watching."""
        rules = [AlertRule(name="test", event_type="PhaseEvent", condition=".confidence < 30")]
        engine = AlertEngine(bus, rules, notifier)
        engine.stop_watching()  # should not raise

    @pytest.mark.asyncio
    async def test_file_change_triggers_reload(self, bus, notifier, tmp_path):
        """Writing to the rules file triggers reload after debounce."""
        try:
            from watchdog.events import FileSystemEventHandler  # noqa: F401
        except ImportError:
            pytest.skip("watchdog not installed")

        # Create a temp rules file
        rules_content = """rules:
  - name: test_rule
    event_type: PhaseEvent
    condition: ".confidence < 30"
    cooldown_seconds: 0
    severity: warning
    channels: [telegram]
"""
        rules_file = tmp_path / "alerting_rules.yaml"
        rules_file.write_text(rules_content)

        rules = load_rules_from_yaml(str(rules_file))
        engine = AlertEngine(bus, rules, notifier)
        await engine.start()
        await bus.start()

        # Start watching
        engine.start_watching(str(rules_file))

        # Modify the file to stricter threshold
        new_content = """rules:
  - name: test_rule
    event_type: PhaseEvent
    condition: ".confidence < 10"
    cooldown_seconds: 0
    severity: warning
    channels: [telegram]
"""
        rules_file.write_text(new_content)

        # Wait for debounce + reload
        await asyncio.sleep(1.5)

        # Verify rules were reloaded (threshold is now < 10)
        from src.services.event_bus import PhaseEvent
        bus.publish(PhaseEvent(symbol="QQQ", confidence=20))
        await asyncio.sleep(0.2)

        await bus.stop()
        engine.stop_watching()

        # 20 is not < 10, so no alert should fire
        assert len(notifier.messages) == 0

    @pytest.mark.asyncio
    async def test_debounce_multiple_writes(self, bus, notifier, tmp_path):
        """Multiple rapid writes only trigger one reload."""
        try:
            from watchdog.events import FileSystemEventHandler  # noqa: F401
        except ImportError:
            pytest.skip("watchdog not installed")

        rules_content = """rules:
  - name: test_rule
    event_type: PhaseEvent
    condition: ".confidence < 30"
    cooldown_seconds: 0
    severity: warning
    channels: [telegram]
"""
        rules_file = tmp_path / "alerting_rules.yaml"
        rules_file.write_text(rules_content)

        rules = load_rules_from_yaml(str(rules_file))
        engine = AlertEngine(bus, rules, notifier)
        await engine.start()
        await bus.start()

        engine.start_watching(str(rules_file))

        # Write multiple times rapidly
        for _ in range(5):
            rules_file.write_text(rules_content)
            await asyncio.sleep(0.1)

        # Wait for debounce
        await asyncio.sleep(1.5)

        await bus.stop()
        engine.stop_watching()
        # Should not have crashed — debounce handled it

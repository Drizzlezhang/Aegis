"""Tests for alerting rule engine — rule matching, cooldown, YAML loading."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from src.services.alerting import (
    AlertEngine,
    AlertRule,
    _evaluate_condition,
    load_rules_from_yaml,
)
from src.services.event_bus import (
    AlertEvent,
    DataEvent,
    EventBus,
    EventSeverity,
    PhaseEvent,
)


class FakeNotifier:
    """Fake Telegram notifier for testing."""

    def __init__(self):
        self.messages: list[str] = []

    async def send_message(self, message: str, force: bool = False) -> bool:
        self.messages.append(message)
        return True


class TestConditionEvaluator:
    """Unit tests for the condition evaluator."""

    def test_less_than_true(self):
        evt = PhaseEvent(confidence=20)
        assert _evaluate_condition(evt, ".confidence < 30") is True

    def test_less_than_false(self):
        evt = PhaseEvent(confidence=50)
        assert _evaluate_condition(evt, ".confidence < 30") is False

    def test_greater_than(self):
        evt = PhaseEvent(composite_score=85)
        assert _evaluate_condition(evt, ".composite_score > 80") is True

    def test_equals(self):
        evt = DataEvent(success=False)
        assert _evaluate_condition(evt, ".success == False") is True

    def test_not_equals(self):
        evt = PhaseEvent(transition="markup→distribution")
        assert _evaluate_condition(evt, ".transition != None") is True

    def test_missing_field(self):
        evt = PhaseEvent()
        assert _evaluate_condition(evt, ".nonexistent < 30") is False

    def test_unparseable(self):
        evt = PhaseEvent()
        assert _evaluate_condition(evt, "garbage") is False


class TestAlertEngine:
    """Integration tests for AlertEngine with EventBus."""

    @pytest.fixture
    def bus(self):
        return EventBus()

    @pytest.fixture
    def notifier(self):
        return FakeNotifier()

    @pytest.mark.asyncio
    async def test_rule_fires_on_match(self, bus, notifier):
        """Rule matching triggers notification."""
        rules = [
            AlertRule(
                name="low_confidence",
                event_type="PhaseEvent",
                condition=".confidence < 30",
                cooldown_seconds=0,
            )
        ]
        engine = AlertEngine(bus, rules, notifier)
        await engine.start()
        await bus.start()

        bus.publish(PhaseEvent(symbol="QQQ", confidence=20))
        await asyncio.sleep(0.1)

        await bus.stop()
        assert len(notifier.messages) == 1
        assert "low_confidence" in notifier.messages[0]

    @pytest.mark.asyncio
    async def test_rule_does_not_fire_on_no_match(self, bus, notifier):
        """Rule does not fire when condition is not met."""
        rules = [
            AlertRule(
                name="low_confidence",
                event_type="PhaseEvent",
                condition=".confidence < 30",
                cooldown_seconds=0,
            )
        ]
        engine = AlertEngine(bus, rules, notifier)
        await engine.start()
        await bus.start()

        bus.publish(PhaseEvent(symbol="QQQ", confidence=80))
        await asyncio.sleep(0.1)

        await bus.stop()
        assert len(notifier.messages) == 0

    @pytest.mark.asyncio
    async def test_cooldown_prevents_duplicate(self, bus, notifier):
        """Cooldown prevents repeated firing within the window."""
        rules = [
            AlertRule(
                name="low_confidence",
                event_type="PhaseEvent",
                condition=".confidence < 30",
                cooldown_seconds=60,  # long cooldown
            )
        ]
        engine = AlertEngine(bus, rules, notifier)
        await engine.start()
        await bus.start()

        bus.publish(PhaseEvent(symbol="QQQ", confidence=20))
        await asyncio.sleep(0.05)
        bus.publish(PhaseEvent(symbol="SPY", confidence=25))
        await asyncio.sleep(0.1)

        await bus.stop()
        assert len(notifier.messages) == 1  # only first fires

    @pytest.mark.asyncio
    async def test_alert_event_published(self, bus, notifier):
        """AlertEngine publishes AlertEvent when rule fires."""
        alert_events: list[AlertEvent] = []

        async def alert_handler(event: AlertEvent):
            alert_events.append(event)

        bus.subscribe("AlertEvent", alert_handler)

        rules = [
            AlertRule(
                name="low_confidence",
                event_type="PhaseEvent",
                condition=".confidence < 30",
                cooldown_seconds=0,
            )
        ]
        engine = AlertEngine(bus, rules, notifier)
        await engine.start()
        await bus.start()

        bus.publish(PhaseEvent(symbol="QQQ", confidence=20))
        await asyncio.sleep(0.1)

        await bus.stop()
        assert len(alert_events) == 1
        assert alert_events[0].rule_name == "low_confidence"

    @pytest.mark.asyncio
    async def test_multiple_rules_different_types(self, bus, notifier):
        """Different event types trigger different rules."""
        rules = [
            AlertRule(
                name="low_confidence",
                event_type="PhaseEvent",
                condition=".confidence < 30",
                cooldown_seconds=0,
            ),
            AlertRule(
                name="data_failure",
                event_type="DataEvent",
                condition=".success == False",
                cooldown_seconds=0,
            ),
        ]
        engine = AlertEngine(bus, rules, notifier)
        await engine.start()
        await bus.start()

        bus.publish(PhaseEvent(symbol="QQQ", confidence=20))
        bus.publish(DataEvent(provider="yfinance", symbol="AAPL", success=False))
        await asyncio.sleep(0.1)

        await bus.stop()
        assert len(notifier.messages) == 2

    @pytest.mark.asyncio
    async def test_hot_reload_rules(self, bus, notifier):
        """reload_rules replaces active rule set."""
        rules_v1 = [
            AlertRule(
                name="low_confidence",
                event_type="PhaseEvent",
                condition=".confidence < 30",
                cooldown_seconds=0,
            )
        ]
        engine = AlertEngine(bus, rules_v1, notifier)
        await engine.start()
        await bus.start()

        # Reload with stricter threshold
        rules_v2 = [
            AlertRule(
                name="low_confidence",
                event_type="PhaseEvent",
                condition=".confidence < 10",
                cooldown_seconds=0,
            )
        ]
        engine.reload_rules(rules_v2)

        bus.publish(PhaseEvent(symbol="QQQ", confidence=20))
        await asyncio.sleep(0.1)

        await bus.stop()
        assert len(notifier.messages) == 0  # 20 is not < 10


class TestYamlLoading:
    """Tests for YAML rule loading."""

    def test_load_rules_from_yaml(self):
        yaml_content = """rules:
  - name: test_rule
    event_type: PhaseEvent
    condition: ".confidence < 30"
    cooldown_seconds: 300
    severity: warning
    channels: [telegram]
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            tmp_path = f.name

        try:
            rules = load_rules_from_yaml(tmp_path)
            assert len(rules) == 1
            assert rules[0].name == "test_rule"
            assert rules[0].event_type == "PhaseEvent"
            assert rules[0].cooldown_seconds == 300
        finally:
            Path(tmp_path).unlink()

    def test_load_real_rules_file(self):
        """The bundled alerting_rules.yaml loads without error."""
        rules = load_rules_from_yaml("config/alerting_rules.yaml")
        assert len(rules) >= 5
        rule_names = {r.name for r in rules}
        assert "low_phase_confidence" in rule_names
        assert "data_fetch_failure" in rule_names

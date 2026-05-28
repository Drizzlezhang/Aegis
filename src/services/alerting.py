"""Alerting rule engine — YAML-driven, cooldown-aware, Telegram-backed.

Evaluates jq-like conditions against event fields.  Uses a simple
self-contained evaluator (no jmespath / jq C dependency).
"""

from __future__ import annotations

import logging
import operator
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from src.services.event_bus import AlertEvent, BaseEvent, EventBus, EventSeverity

logger = logging.getLogger(__name__)


# ── condition evaluator (self-contained, no jmespath) ───────────────────────

_OPERATORS: dict[str, Callable[[Any, Any], bool]] = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
}


def _evaluate_condition(event: BaseEvent, condition: str) -> bool:
    """Evaluate a simple condition string like ``.confidence < 30``.

    Supports: field access via ``.field``, comparison operators.
    """
    condition = condition.strip()
    for op_str in ["<=", ">=", "!=", "==", "<", ">"]:
        if op_str in condition:
            left_raw, _, right_raw = condition.partition(op_str)
            break
    else:
        logger.warning("Unparseable condition: %s", condition)
        return False

    field_name = left_raw.strip().lstrip(".")
    right_raw = right_raw.strip()

    # Get field value from event
    if not hasattr(event, field_name):
        logger.warning("Event %s has no field %s", event.event_type, field_name)
        return False

    left_val = getattr(event, field_name)

    # Parse right value
    right_val: Any
    if right_raw == "True":
        right_val = True
    elif right_raw == "False":
        right_val = False
    elif right_raw == "None":
        right_val = None
    else:
        try:
            if "." in right_raw:
                right_val = float(right_raw)
            else:
                right_val = int(right_raw)
        except ValueError:
            right_val = right_raw.strip("\"'")

    op_func = _OPERATORS.get(op_str)
    if op_func is None:
        return False

    try:
        return op_func(left_val, right_val)
    except TypeError:
        return False


# ── rule model ──────────────────────────────────────────────────────────────


class AlertRule(BaseModel):
    """A single alerting rule, deserialized from YAML."""

    name: str
    event_type: str
    condition: str
    cooldown_seconds: int = 300
    severity: EventSeverity = EventSeverity.WARNING
    channels: list[str] = Field(default_factory=lambda: ["telegram"])


class AlertRulesConfig(BaseModel):
    """Container for a list of alert rules."""

    rules: list[AlertRule] = Field(default_factory=list)


# ── engine ──────────────────────────────────────────────────────────────────


@dataclass
class _RuleState:
    last_fired: float = 0.0


class AlertEngine:
    """Subscribes to EventBus, evaluates rules, sends alerts via notifier."""

    def __init__(
        self,
        event_bus: EventBus,
        rules: list[AlertRule],
        notifier: Any = None,  # TelegramNotifier | None
    ) -> None:
        self._bus = event_bus
        self._rules = rules
        self._notifier = notifier
        self._states: dict[str, _RuleState] = {
            r.name: _RuleState() for r in rules
        }

    async def start(self) -> None:
        """Subscribe to all event types referenced by rules."""
        event_types = {r.event_type for r in self._rules}
        for etype in event_types:
            self._bus.subscribe(etype, self._on_event)

    async def _on_event(self, event: BaseEvent) -> None:
        for rule in self._rules:
            if rule.event_type != event.event_type:
                continue
            if not _evaluate_condition(event, rule.condition):
                continue

            state = self._states[rule.name]
            now = time.monotonic()
            if now - state.last_fired < rule.cooldown_seconds:
                continue

            state.last_fired = now
            await self._fire(rule, event)

    async def _fire(self, rule: AlertRule, event: BaseEvent) -> None:
        logger.info(
            "Alert rule %s fired (severity=%s, event=%s)",
            rule.name,
            rule.severity,
            event.event_type,
        )
        # Publish AlertEvent so other subscribers can react
        self._bus.publish(
            AlertEvent(
                rule_name=rule.name,
                message=f"Rule {rule.name}: {rule.condition} matched",
                severity=rule.severity,
            )
        )
        # Send via Telegram if configured
        if self._notifier and "telegram" in rule.channels:
            try:
                await self._notifier.send_message(
                    f"🚨 *{rule.name}*\n"
                    f"Condition: `{rule.condition}`\n"
                    f"Severity: {rule.severity.value}\n"
                    f"Event: {event.event_type}",
                    force=True,
                )
            except Exception:
                logger.exception("Failed to send alert via Telegram")

    def reload_rules(self, rules: list[AlertRule]) -> None:
        """Hot-reload rules without restarting."""
        self._rules = rules
        self._states = {r.name: _RuleState() for r in rules}


def load_rules_from_yaml(path: str | Path) -> list[AlertRule]:
    """Load alert rules from a YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)
    config = AlertRulesConfig.model_validate(data)
    return config.rules

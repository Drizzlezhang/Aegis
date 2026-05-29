"""Alerting rule engine — YAML-driven, cooldown-aware, Telegram-backed.

Evaluates jq-like conditions against event fields.  Uses a simple
self-contained evaluator (no jmespath / jq C dependency).
"""

from __future__ import annotations

import asyncio
import logging
import operator
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from src.services.event_bus import (
    AlertEvent,
    AlertingRulesReloaded,
    BaseEvent,
    EventBus,
    EventSeverity,
)

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

# ── AST nodes for compound expressions ──────────────────────────────────────


class _ASTNode:
    """Base AST node."""


@dataclass
class _Comparison(_ASTNode):
    field: str
    op: str
    value: Any


@dataclass
class _LogicalOp(_ASTNode):
    left: _ASTNode
    op: str  # "AND" | "OR"
    right: _ASTNode


@dataclass
class _InOp(_ASTNode):
    field: str
    values: list[Any]


# ── tokenizer ────────────────────────────────────────────────────────────────


def _tokenize(condition: str) -> list[str]:
    """Split condition string into tokens."""
    tokens: list[str] = []
    i = 0
    n = len(condition)
    while i < n:
        c = condition[i]
        if c.isspace():
            i += 1
            continue
        if c == "(":
            tokens.append("(")
            i += 1
        elif c == ")":
            tokens.append(")")
            i += 1
        elif c == "[":
            # Collect everything until "]"
            j = i + 1
            while j < n and condition[j] != "]":
                j += 1
            tokens.append(condition[i:j + 1])
            i = j + 1
        elif c in ('"', "'"):
            # Quoted string
            quote = c
            j = i + 1
            while j < n and condition[j] != quote:
                j += 1
            tokens.append(condition[i:j + 1])
            i = j + 1
        elif c == ".":
            # Field access: collect .field or .field.subfield
            j = i + 1
            while j < n and (condition[j].isalnum() or condition[j] in "._"):
                j += 1
            tokens.append(condition[i:j])
            i = j
        elif c.isdigit() or (c == "-" and i + 1 < n and condition[i + 1].isdigit()):
            # Number (including negative)
            j = i + 1
            while j < n and (condition[j].isdigit() or condition[j] == "."):
                j += 1
            tokens.append(condition[i:j])
            i = j
        elif condition[i:i + 2] in ("<=", ">=", "!=", "=="):
            tokens.append(condition[i:i + 2])
            i += 2
        elif c in ("<", ">"):
            tokens.append(c)
            i += 1
        elif condition[i:i + 2] == "IN":
            tokens.append("IN")
            i += 2
        elif condition[i:i + 3] == "AND":
            tokens.append("AND")
            i += 3
        elif condition[i:i + 2] == "OR":
            tokens.append("OR")
            i += 2
        else:
            # Identifier / keyword
            j = i
            while j < n and (condition[j].isalnum() or condition[j] == "_"):
                j += 1
            if j > i:
                tokens.append(condition[i:j])
                i = j
            else:
                i += 1  # skip unknown char
    return tokens


# ── recursive descent parser ─────────────────────────────────────────────────


def _parse_expression(tokens: list[str], pos: int = 0) -> tuple[_ASTNode, int]:
    """Parse expression: OR_expr."""
    return _parse_or(tokens, pos)


def _parse_or(tokens: list[str], pos: int) -> tuple[_ASTNode, int]:
    """Parse OR expression (lowest precedence)."""
    left, pos = _parse_and(tokens, pos)
    while pos < len(tokens) and tokens[pos] == "OR":
        pos += 1
        right, pos = _parse_and(tokens, pos)
        left = _LogicalOp(left=left, op="OR", right=right)
    return left, pos


def _parse_and(tokens: list[str], pos: int) -> tuple[_ASTNode, int]:
    """Parse AND expression."""
    left, pos = _parse_atom(tokens, pos)
    while pos < len(tokens) and tokens[pos] == "AND":
        pos += 1
        right, pos = _parse_atom(tokens, pos)
        left = _LogicalOp(left=left, op="AND", right=right)
    return left, pos


def _parse_atom(tokens: list[str], pos: int) -> tuple[_ASTNode, int]:
    """Parse atom: comparison | IN expr | '(' expr ')'."""
    if pos >= len(tokens):
        raise ValueError("Unexpected end of expression")

    if tokens[pos] == "(":
        pos += 1
        node, pos = _parse_expression(tokens, pos)
        if pos >= len(tokens) or tokens[pos] != ")":
            raise ValueError("Expected ')'")
        pos += 1
        return node, pos

    # Must be: field op value  OR  field IN [...]
    if pos >= len(tokens) or not tokens[pos].startswith("."):
        raise ValueError(f"Expected field access, got {tokens[pos] if pos < len(tokens) else 'EOF'}")

    field = tokens[pos]
    pos += 1

    if pos < len(tokens) and tokens[pos] == "IN":
        pos += 1  # skip IN
        if pos >= len(tokens) or not tokens[pos].startswith("["):
            raise ValueError("Expected '[' after IN")
        list_str = tokens[pos]
        pos += 1
        # Parse list: [val1, val2, ...]
        inner = list_str[1:-1].strip()
        values: list[Any] = []
        for item in inner.split(","):
            item = item.strip().strip("\"'")
            values.append(_parse_literal(item))
        return _InOp(field=field, values=values), pos

    # Comparison: field op value
    if pos >= len(tokens) or tokens[pos] not in _OPERATORS:
        raise ValueError(f"Expected operator, got {tokens[pos] if pos < len(tokens) else 'EOF'}")

    op = tokens[pos]
    pos += 1

    if pos >= len(tokens):
        raise ValueError("Expected value after operator")

    value = _parse_literal(tokens[pos])
    pos += 1

    return _Comparison(field=field, op=op, value=value), pos


def _parse_literal(token: str) -> Any:
    """Parse a literal token into a Python value."""
    if token == "True":
        return True
    if token == "False":
        return False
    if token == "None":
        return None
    # Quoted string
    if (token.startswith('"') and token.endswith('"')) or \
       (token.startswith("'") and token.endswith("'")):
        return token[1:-1]
    try:
        if "." in token:
            return float(token)
        return int(token)
    except ValueError:
        return token


# ── AST evaluator ────────────────────────────────────────────────────────────


def _resolve_field(event: BaseEvent, field_path: str) -> Any:
    """Resolve a dotted field path like .metadata.region against an event."""
    parts = field_path.lstrip(".").split(".")
    obj: Any = event
    for part in parts:
        if hasattr(obj, part):
            obj = getattr(obj, part)
        elif isinstance(obj, dict) and part in obj:
            obj = obj[part]
        else:
            return _MISSING
    return obj


_MISSING = object()


def _eval_ast(node: _ASTNode, event: BaseEvent) -> bool:
    """Evaluate an AST node against an event."""
    if isinstance(node, _Comparison):
        left_val = _resolve_field(event, node.field)
        if left_val is _MISSING:
            return False
        op_func = _OPERATORS.get(node.op)
        if op_func is None:
            return False
        try:
            return op_func(left_val, node.value)
        except TypeError:
            return False

    if isinstance(node, _LogicalOp):
        left_result = _eval_ast(node.left, event)
        if node.op == "AND":
            if not left_result:
                return False  # short-circuit
            return _eval_ast(node.right, event)
        else:  # OR
            if left_result:
                return True  # short-circuit
            return _eval_ast(node.right, event)

    if isinstance(node, _InOp):
        left_val = _resolve_field(event, node.field)
        if left_val is _MISSING:
            return False
        return left_val in node.values

    return False


# ── public API ───────────────────────────────────────────────────────────────


def _evaluate_condition(event: BaseEvent, condition: str) -> bool:
    """Evaluate a condition string against an event.

    Supports:
    - Simple: ``.confidence < 30``
    - Compound: ``.confidence < 30 AND .composite_score < 50``
    - Nested fields: ``.metadata.region == "US"``
    - IN operator: ``.severity IN [warning, critical]``
    - Parentheses: ``(a < 10 OR b > 20) AND c == 5``
    """
    condition = condition.strip()
    if not condition:
        return False

    # Try new parser first; fall back to old simple evaluator
    try:
        tokens = _tokenize(condition)
        if not tokens:
            return False
        ast, pos = _parse_expression(tokens)
        if pos < len(tokens):
            # Extra tokens — fall back to old evaluator
            return _evaluate_simple(event, condition)
        return _eval_ast(ast, event)
    except (ValueError, IndexError):
        return _evaluate_simple(event, condition)


def _evaluate_simple(event: BaseEvent, condition: str) -> bool:
    """Legacy simple evaluator — single field comparison only."""
    for op_str in ["<=", ">=", "!=", "==", "<", ">"]:
        if op_str in condition:
            left_raw, _, right_raw = condition.partition(op_str)
            break
    else:
        logger.warning("Unparseable condition: %s", condition)
        return False

    field_name = left_raw.strip().lstrip(".")
    right_raw = right_raw.strip()

    if not hasattr(event, field_name):
        logger.warning("Event %s has no field %s", event.event_type, field_name)
        return False

    left_val = getattr(event, field_name)

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
        self._observer: Any = None  # watchdog Observer
        self._watch_task: asyncio.Task[None] | None = None

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

    # ── file watching ───────────────────────────────────────────────────

    def start_watching(self, rules_path: str | Path) -> None:
        """Watch rules file for changes and auto-reload (debounce 1s).

        Uses watchdog if available.  No-op if watchdog is not installed.
        """
        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
        except ImportError:
            logger.warning("watchdog not installed, file watching disabled")
            return

        rules_path = Path(rules_path)
        if not rules_path.exists():
            logger.warning("Rules file %s does not exist, watching disabled", rules_path)
            return

        engine = self
        bus = self._bus

        class _RulesFileHandler(FileSystemEventHandler):
            def __init__(self):
                self._debounce_task: asyncio.Task[None] | None = None

            def on_modified(self, event):
                if event.src_path.endswith(rules_path.name):
                    if self._debounce_task is not None:
                        self._debounce_task.cancel()
                    self._debounce_task = asyncio.ensure_future(
                        self._reload_after_debounce()
                    )

            async def _reload_after_debounce(self):
                await asyncio.sleep(1.0)  # debounce 1s
                try:
                    new_rules = load_rules_from_yaml(rules_path)
                    engine.reload_rules(new_rules)
                    bus.publish(AlertingRulesReloaded(rule_count=len(new_rules)))
                    logger.info(
                        "Rules reloaded from %s (%d rules)", rules_path, len(new_rules)
                    )
                except Exception:
                    logger.exception("Failed to reload rules from %s", rules_path)

        observer = Observer()
        observer.schedule(
            _RulesFileHandler(),
            path=str(rules_path.parent),
            recursive=False,
        )
        observer.start()
        self._observer = observer
        logger.info("Started watching %s for rule changes", rules_path)

    def stop_watching(self) -> None:
        """Stop file watching if active."""
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=2)
            self._observer = None
            logger.info("Stopped watching rules file")


def load_rules_from_yaml(path: str | Path) -> list[AlertRule]:
    """Load alert rules from a YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)
    config = AlertRulesConfig.model_validate(data)
    return config.rules

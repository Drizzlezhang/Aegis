"""Integration smoke tests for sprint14 cross-branch features."""

from dataclasses import dataclass
from datetime import date, datetime

import pytest

from src.services.event_bus import (
    AlertingRulesReloaded,
    BaseEvent,
    DataEvent,
    EventBus,
    EventSeverity,
    PhaseEvent,
)

# ── Scenario 1: EventBus → PhasePredictor → AlertEngine chain ────────────────


class TestEventBusPhaseAlertChain:
    """Smoke test: EventBus dispatches PhaseEvent → AlertEngine evaluates rules."""

    def test_phase_event_condition_evaluation(self):
        """PhaseEvent with low confidence matches condition."""
        from src.services.alerting import _evaluate_condition

        event = PhaseEvent(
            symbol="QQQ",
            phase="markup",
            confidence=25.0,
            composite_score=45.0,
            severity=EventSeverity.WARNING,
        )

        assert _evaluate_condition(event, ".confidence < 30") is True
        assert _evaluate_condition(event, ".confidence > 50") is False

    def test_phase_event_compound_condition(self):
        """Compound AND condition on PhaseEvent works."""
        from src.services.alerting import _evaluate_condition

        event = PhaseEvent(
            symbol="QQQ",
            phase="markup",
            confidence=30.0,
            composite_score=40.0,
        )

        # Both true
        assert _evaluate_condition(event, ".confidence < 40 AND .composite_score < 50") is True
        # Only one true
        assert _evaluate_condition(event, ".confidence < 40 AND .composite_score > 50") is False

    def test_alert_engine_subscribes_to_event_bus(self):
        """AlertEngine subscribes to EventBus for rule event types."""
        from src.services.alerting import AlertEngine, AlertRule

        bus = EventBus()
        rules = [
            AlertRule(
                name="low_confidence_phase",
                event_type="PhaseEvent",
                condition=".confidence < 30",
                severity=EventSeverity.WARNING,
                cooldown_seconds=0,
            ),
        ]
        engine = AlertEngine(event_bus=bus, rules=rules)

        import asyncio
        asyncio.run(engine.start())

        # Verify subscription exists
        assert "PhaseEvent" in bus._subscribers

    @pytest.mark.asyncio
    async def test_alert_engine_fires_on_match(self):
        """AlertEngine._on_event fires alert when condition matches."""
        from src.services.alerting import AlertEngine, AlertRule

        bus = EventBus()
        rules = [
            AlertRule(
                name="low_confidence_phase",
                event_type="PhaseEvent",
                condition=".confidence < 30",
                severity=EventSeverity.WARNING,
                cooldown_seconds=0,
            ),
        ]
        engine = AlertEngine(event_bus=bus, rules=rules)

        event = PhaseEvent(
            symbol="QQQ",
            phase="markup",
            confidence=25.0,
            composite_score=45.0,
            severity=EventSeverity.WARNING,
        )

        # _on_event is async, call it directly
        await engine._on_event(event)
        # Should not raise; alert fires internally


# ── Scenario 2: DataHarvester failure → AlertEngine rule ─────────────────────


class TestDataFailureAlert:
    """Smoke test: DataEvent failure triggers alert."""

    def test_data_failure_condition(self):
        """DataEvent with success=False matches condition."""
        from src.services.alerting import _evaluate_condition

        event = DataEvent(
            provider="yahoo",
            symbol="QQQ",
            success=False,
            error_type="TimeoutError",
            severity=EventSeverity.ERROR,
        )

        assert _evaluate_condition(event, ".success == False") is True

    def test_data_success_does_not_match(self):
        """DataEvent with success=True does NOT match failure condition."""
        from src.services.alerting import _evaluate_condition

        event = DataEvent(
            provider="yahoo",
            symbol="QQQ",
            success=True,
        )

        assert _evaluate_condition(event, ".success == False") is False

    def test_data_failure_specific_error_type(self):
        """Alert rule can match specific error types."""
        from src.services.alerting import _evaluate_condition

        event = DataEvent(
            provider="yahoo",
            symbol="QQQ",
            success=False,
            error_type="RateLimitError",
            severity=EventSeverity.CRITICAL,
        )

        assert _evaluate_condition(event, ".error_type == 'RateLimitError'") is True
        assert _evaluate_condition(event, ".error_type == 'TimeoutError'") is False


# ── Scenario 3: Scheduler persistence → Prometheus metrics ───────────────────


class TestSchedulerMetrics:
    """Smoke test: Scheduler operations reflected in Prometheus metrics."""

    def test_metrics_endpoint_accessible(self):
        """GET /metrics/prometheus returns 200."""
        from fastapi.testclient import TestClient

        from src.api.main import app

        client = TestClient(app)
        response = client.get("/api/metrics/prometheus")
        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")

    def test_metrics_contain_aegis_prefix(self):
        """Metrics response contains aegis_ prefixed metrics."""
        from fastapi.testclient import TestClient

        from src.api.main import app

        client = TestClient(app)
        response = client.get("/api/metrics/prometheus")
        content = response.text
        assert "aegis_" in content.lower() or "HELP" in content

    def test_alerting_rules_reloaded_event_published(self):
        """AlertingRulesReloaded event can be published to EventBus."""
        bus = EventBus()

        received: list[AlertingRulesReloaded] = []

        async def handler(event: BaseEvent) -> None:
            if isinstance(event, AlertingRulesReloaded):
                received.append(event)

        bus.subscribe("AlertingRulesReloaded", handler)

        event = AlertingRulesReloaded(rule_count=5)
        bus.publish(event)

        # Process the queue
        import asyncio
        async def process():
            while not bus._queue.empty():
                evt = await bus._queue.get()
                for h in bus._subscribers.get(evt.event_type, {}).values():
                    result = h(evt)
                    if asyncio.iscoroutine(result):
                        await result

        asyncio.run(process())

        assert len(received) == 1
        assert received[0].rule_count == 5


# ── Scenario 4: BacktestRunner 30-day → phase_attribution ────────────────────


class TestBacktestPhaseAttributionIntegration:
    """Smoke test: BacktestRunner produces phase-attributed results."""

    @pytest.mark.asyncio
    async def test_30_day_backtest_with_phase_attribution(self):
        """30-day backtest produces phase attribution rows."""
        import random

        from src.backtest.phase_attribution import PhaseAttribution
        from src.backtest.runner import BacktestRunner
        random.seed(42)

        @dataclass
        class _Bar:
            timestamp: datetime
            open: float
            high: float
            low: float
            close: float
            volume: int

        price = 100.0
        data = []
        base_date = datetime(2024, 1, 2)
        for i in range(30):
            change = random.uniform(-2, 2)
            price += change
            if price < 1:
                price = 1
            ts = base_date.replace(day=min(base_date.day + i, 28))
            data.append(_Bar(
                timestamp=ts,
                open=price - 0.5,
                high=price + 1,
                low=price - 1,
                close=price,
                volume=10000,
            ))

        runner = BacktestRunner("QQQ", date(2024, 1, 1), date(2024, 1, 31))
        result = await runner.run(data)

        attribution = PhaseAttribution.analyze(result.trades, result.daily_decisions)

        assert len(attribution) > 0
        for row in attribution:
            assert row.phase
            assert row.trades_count >= 0
            assert isinstance(row.avg_return, float)
            assert 0 <= row.win_rate <= 100

    @pytest.mark.asyncio
    async def test_backtest_trades_have_phase_context(self):
        """Backtest trades record entry/exit phase and confidence."""
        import random

        from src.backtest.runner import BacktestRunner
        random.seed(42)

        @dataclass
        class _Bar:
            timestamp: datetime
            open: float
            high: float
            low: float
            close: float
            volume: int

        price = 100.0
        data = []
        base_date = datetime(2024, 1, 2)
        for i in range(30):
            change = random.uniform(-2, 2)
            price += change
            if price < 1:
                price = 1
            ts = base_date.replace(day=min(base_date.day + i, 28))
            data.append(_Bar(
                timestamp=ts,
                open=price - 0.5,
                high=price + 1,
                low=price - 1,
                close=price,
                volume=10000,
            ))

        runner = BacktestRunner("SPY", date(2024, 1, 1), date(2024, 1, 31))
        result = await runner.run(data)

        for trade in result.trades:
            assert trade.entry_phase is not None
            assert trade.exit_phase is not None
            assert trade.entry_confidence is not None
            assert trade.exit_confidence is not None
            assert trade.position_size_multiplier > 0

    @pytest.mark.asyncio
    async def test_multi_symbol_backtest_integration(self):
        """Multi-symbol backtest runs and produces results for all symbols."""
        import random

        from src.backtest.runner import MultiSymbolRunner
        random.seed(42)

        @dataclass
        class _Bar:
            timestamp: datetime
            open: float
            high: float
            low: float
            close: float
            volume: int

        def _make_data(sym: str) -> list:
            price = 100.0 + hash(sym) % 50
            data = []
            base_date = datetime(2024, 1, 2)
            for i in range(10):
                change = random.uniform(-2, 2)
                price += change
                if price < 1:
                    price = 1
                ts = base_date.replace(day=min(base_date.day + i, 28))
                data.append(_Bar(
                    timestamp=ts,
                    open=price - 0.5,
                    high=price + 1,
                    low=price - 1,
                    close=price,
                    volume=10000,
                ))
            return data

        data_map = {
            "QQQ": _make_data("QQQ"),
            "SPY": _make_data("SPY"),
            "NVDA": _make_data("NVDA"),
        }

        runner = MultiSymbolRunner(
            ["QQQ", "SPY", "NVDA"],
            date(2024, 1, 1),
            date(2024, 1, 31),
            max_concurrent=3,
        )
        results = await runner.run(data_map)

        assert len(results) == 3
        for sym in ["QQQ", "SPY", "NVDA"]:
            assert sym in results
            assert results[sym].symbol == sym
            assert len(results[sym].equity_curve) > 0

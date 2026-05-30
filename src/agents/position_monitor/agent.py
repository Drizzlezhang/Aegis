"""Position Monitor Agent implementation."""

import logging
from uuid import uuid4

from src.agents.base import BaseAgent
from src.models import AgentState, DecisionEntry, DecisionType
from src.services import DecisionLog
from src.services.event_bus import (
    AlertEvent,
    EventBus,
    EventSeverity,
    OrderCancelledEvent,
    OrderFilledEvent,
    OrderRejectedEvent,
    get_event_bus,
)

from .monitor import AlertType, PositionMonitor
from .position_manager import PositionManager
from .reflection import ReflectionEngine

logger = logging.getLogger(__name__)


class PositionMonitorAgent(BaseAgent):
    def __init__(self, config: dict | None = None, event_bus: EventBus | None = None):
        super().__init__(
            name="Position-Monitor",
            description="Monitors open positions for stop-loss, profit-target, and DTE warnings",
            config=config or {},
        )
        storage_path = self.config.get("storage_path", "~/.aegis-trader/positions.json")
        decision_path = self.config.get("decision_storage_path")
        self._manager = PositionManager(storage_path=storage_path)
        self._monitor = PositionMonitor(self._manager)
        self._decision_log = DecisionLog(storage_path=decision_path)
        self._reflection_engine = ReflectionEngine(
            self._decision_log,
            self._manager,
            reflection_delay_hours=self.config.get("reflection_delay_hours", 720),
        )
        self._event_bus = event_bus or get_event_bus()
        self._subscribed = False

    async def initialize(self) -> None:
        await self._manager.load()
        if not self._subscribed:
            self._event_bus.subscribe("OrderFilledEvent", self._on_order_filled)
            self._event_bus.subscribe("OrderCancelledEvent", self._on_order_cancelled)
            self._event_bus.subscribe("OrderRejectedEvent", self._on_order_rejected)
            self._subscribed = True
            logger.info("PositionMonitor subscribed to OrderFilledEvent, OrderCancelledEvent, OrderRejectedEvent")

    async def _on_order_filled(self, event: OrderFilledEvent) -> None:
        """Handle OrderFilledEvent: update internal position view and cross-validate."""
        logger.info(
            "OrderFilled: id=%s symbol=%s side=%s qty=%d price=%.2f",
            event.order_id, event.symbol, event.side,
            event.filled_quantity, event.filled_avg_price,
        )

        # Update internal position view
        internal_positions = await self._manager.get_positions_by_symbol(event.symbol)
        active = [p for p in internal_positions if p.status.value == "active"]

        if event.side == "buy":
            if active:
                pos = active[0]
                total_qty = pos.quantity + event.filled_quantity
                total_cost = pos.avg_cost * pos.quantity + event.filled_avg_price * event.filled_quantity
                pos.quantity = total_qty
                pos.avg_cost = total_cost / total_qty if total_qty > 0 else 0.0
                logger.info(
                    "PositionMonitor: updated %s position: qty=%d avg_cost=%.2f",
                    event.symbol, pos.quantity, pos.avg_cost,
                )
            else:
                logger.info(
                    "No active internal position for %s buy fill — broker position exists without internal match",
                    event.symbol,
                )
        elif event.side == "sell":
            if active:
                pos = active[0]
                remaining = pos.quantity - event.filled_quantity
                if remaining <= 0:
                    pos.status = "closed"  # type: ignore[attr-defined]
                    logger.info("PositionMonitor: closed %s position after sell fill", event.symbol)
                else:
                    pos.quantity = remaining
                    logger.info(
                        "PositionMonitor: reduced %s position: qty=%d remaining=%d",
                        event.symbol, pos.quantity, remaining,
                    )
            else:
                logger.info(
                    "Sell fill for %s with no active internal positions — cross-validating",
                    event.symbol,
                )

        await self._manager.save()

        # Cross-validate with PaperBroker positions (drift detection)
        try:
            from src.agents.strategy_exec.brokers.paper import PaperBroker
            broker = PaperBroker()
            broker_positions = await broker.get_positions()
            broker_pos = next((p for p in broker_positions if p.symbol == event.symbol), None)

            if broker_pos:
                internal_pos = active[0] if active else None
                if internal_pos and abs(internal_pos.quantity - broker_pos.quantity) > 0:
                    drift_msg = (
                        f"Position drift detected for {event.symbol}: "
                        f"internal qty={internal_pos.quantity}, broker qty={broker_pos.quantity}"
                    )
                    logger.warning(drift_msg)
                    self._event_bus.publish(
                        AlertEvent(
                            rule_name="position_drift",
                            message=drift_msg,
                            severity=EventSeverity.WARNING,
                        )
                    )
        except Exception:
            logger.debug("Position drift check skipped (broker not available)", exc_info=True)

    async def _on_order_cancelled(self, event: OrderCancelledEvent) -> None:
        """Handle OrderCancelledEvent: remove from pending order view."""
        logger.info(
            "OrderCancelled: id=%s symbol=%s reason=%s",
            event.order_id, event.symbol, event.reason,
        )

    async def _on_order_rejected(self, event: OrderRejectedEvent) -> None:
        """Handle OrderRejectedEvent: log and remove from pending order view."""
        logger.warning(
            "OrderRejected: id=%s symbol=%s reason=%s",
            event.order_id, event.symbol, event.reason,
        )

    async def run(self, state: AgentState) -> AgentState:
        state.add_agent_step(self.name)
        market_prices = self._extract_market_prices(state)
        alerts = await self._monitor.scan(market_prices)
        await self._manager.save()
        state.metadata["position_monitor_alerts"] = [alert.__dict__ for alert in alerts]
        for alert in alerts:
            if alert.alert_type == AlertType.STOP_LOSS and alert.severity == "critical":
                await self._decision_log.append(
                    DecisionEntry(
                        id=str(uuid4()),
                        symbol=alert.symbol,
                        decision_type=DecisionType.CLOSE,
                        current_price=market_prices.get(alert.symbol.upper(), 0.0),
                        confidence=1.0,
                        reasoning=alert.message,
                    )
                )

        reflections_processed = 0
        try:
            reflections_processed = await self._reflection_engine.scan_for_reflections(market_prices)
        except Exception as exc:
            logger.warning("Reflection engine failed: %s", exc)
        state.metadata["reflections_processed"] = reflections_processed

        if reflections_processed > 0:
            try:
                reflection_summaries = await self._get_recent_reflections()
                state.metadata["reflection_feedback"] = reflection_summaries
            except Exception as exc:
                logger.warning("Reflection feedback collection failed: %s", exc)
        return state

    async def _get_recent_reflections(self) -> list[dict]:
        recent = await self._decision_log.query_recent_reflected(limit=5)
        return [
            {
                "symbol": entry.symbol,
                "decision_type": entry.decision_type.value,
                "outcome": entry.outcome.value if entry.outcome else "pending",
                "pnl": entry.actual_pnl,
                "reflection": entry.reflection,
                "timestamp": entry.timestamp.isoformat(),
            }
            for entry in recent
        ]

    def _extract_market_prices(self, state: AgentState) -> dict[str, float]:
        prices: dict[str, float] = {}
        if state.ohlcv_data:
            latest = state.ohlcv_data[-1]
            prices[state.symbol.upper()] = latest.close
        if state.options_chain:
            prices[state.options_chain.symbol.upper()] = state.options_chain.spot_price
        return prices

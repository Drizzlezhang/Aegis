"""Position Monitor Agent implementation.

TODO(sprint16): Reconcile with BacktestStore instead of the removed paper broker.
Currently monitors internal positions only (stop-loss, profit-target, DTE).
"""

import logging
from uuid import uuid4

from src.agents.base import BaseAgent
from src.models import AgentState, DecisionEntry, DecisionType
from src.services import DecisionLog
from src.services.event_bus import (
    EventBus,
    StrategySignalEvent,
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
            self._event_bus.subscribe("StrategySignalEvent", self._on_strategy_signal)
            self._subscribed = True
            logger.info("PositionMonitor subscribed to StrategySignalEvent")

    async def _on_strategy_signal(self, event: StrategySignalEvent) -> None:
        """Handle StrategySignalEvent: log signal for future BacktestStore reconciliation."""
        logger.info(
            "StrategySignal: symbol=%s action=%s rationale=%s",
            event.symbol, event.action, event.rationale,
        )
        # TODO(sprint16): Reconcile with BacktestStore positions

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

"""Position Monitor Agent implementation."""

import logging
from uuid import uuid4

from src.agents.base import BaseAgent
from src.models import AgentState, DecisionEntry, DecisionType
from src.services import DecisionLog

from .monitor import AlertType, PositionMonitor
from .position_manager import PositionManager
from .reflection import ReflectionEngine

logger = logging.getLogger(__name__)


class PositionMonitorAgent(BaseAgent):
    def __init__(self, config: dict | None = None):
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

    async def initialize(self) -> None:
        await self._manager.load()

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
        return state

    def _extract_market_prices(self, state: AgentState) -> dict[str, float]:
        prices: dict[str, float] = {}
        if state.ohlcv_data:
            latest = state.ohlcv_data[-1]
            prices[state.symbol.upper()] = latest.close
        if state.options_chain:
            prices[state.options_chain.symbol.upper()] = state.options_chain.spot_price
        return prices

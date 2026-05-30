"""Portfolio Service — aggregates cash, positions, PnL, and equity curve."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from src.agents.strategy_exec.brokers.base import BrokerBase
from src.models.paper import AccountSnapshot

logger = logging.getLogger(__name__)


class PortfolioService:
    """Aggregates portfolio state from a broker and persists equity curve history.

    Features:
    - Cash, positions, PnL, equity aggregation
    - Historical equity curve persistence (JSON file)
    - Snapshot recording at configurable intervals
    """

    def __init__(
        self,
        broker: BrokerBase,
        history_path: str = "~/.aegis-trader/equity_curve.json",
    ) -> None:
        self._broker = broker
        self._history_path = Path(history_path).expanduser()
        self._history_path.parent.mkdir(parents=True, exist_ok=True)
        self._equity_curve: list[dict] = []
        self._load_history()

    async def get_snapshot(self) -> AccountSnapshot:
        """Get current portfolio snapshot from broker."""
        return await self._broker.get_balance()

    async def record_snapshot(self) -> AccountSnapshot:
        """Record current portfolio state to equity curve history."""
        snapshot = await self.get_snapshot()
        entry = {
            "timestamp": datetime.now().isoformat(),
            "cash": snapshot.cash,
            "equity": snapshot.equity,
            "buying_power": snapshot.buying_power,
            "total_pnl": snapshot.total_pnl,
            "total_pnl_pct": snapshot.total_pnl_pct,
            "position_count": len(snapshot.positions),
        }
        self._equity_curve.append(entry)
        self._save_history()
        return snapshot

    def get_equity_curve(self, limit: int | None = None) -> list[dict]:
        """Get historical equity curve entries.

        Args:
            limit: Max number of entries to return (most recent first).

        Returns:
            List of equity curve entries.
        """
        entries = list(self._equity_curve)
        if limit is not None:
            entries = entries[-limit:]
        return entries

    def get_stats(self) -> dict:
        """Get portfolio statistics from equity curve."""
        if not self._equity_curve:
            return {
                "total_snapshots": 0,
                "start_equity": 0.0,
                "current_equity": 0.0,
                "total_return_pct": 0.0,
                "max_equity": 0.0,
                "min_equity": 0.0,
                "max_drawdown_pct": 0.0,
            }

        equities = [e["equity"] for e in self._equity_curve]
        start = equities[0]
        current = equities[-1]
        total_return = ((current - start) / start * 100) if start > 0 else 0.0

        # Max drawdown
        peak = equities[0]
        max_dd = 0.0
        for eq in equities:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100 if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

        return {
            "total_snapshots": len(self._equity_curve),
            "start_equity": start,
            "current_equity": current,
            "total_return_pct": round(total_return, 2),
            "max_equity": max(equities),
            "min_equity": min(equities),
            "max_drawdown_pct": round(max_dd, 2),
        }

    def reset(self) -> None:
        """Clear equity curve history."""
        self._equity_curve = []
        self._save_history()
        logger.info("Portfolio equity curve reset")

    def _save_history(self) -> None:
        self._history_path.write_text(
            json.dumps(self._equity_curve, indent=2), encoding="utf-8"
        )

    def _load_history(self) -> None:
        if not self._history_path.exists():
            return
        try:
            data = json.loads(self._history_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                self._equity_curve = data
        except (json.JSONDecodeError, OSError):
            logger.warning("Failed to load equity curve history, starting fresh")
            self._equity_curve = []

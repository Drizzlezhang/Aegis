"""Portfolio Service — aggregates cash, positions, PnL, and equity curve."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

import aiosqlite

from src.agents.strategy_exec.brokers.base import BrokerBase
from src.models.paper import AccountSnapshot

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "~/.aegis-trader/paper_state.sqlite"


class PortfolioService:
    """Aggregates portfolio state from a broker and persists equity curve history.

    Features:
    - Cash, positions, PnL, equity aggregation
    - Historical equity curve persistence (SQLite, shared with PaperBroker)
    - Snapshot recording at configurable intervals
    - Automatic migration from legacy JSON file
    """

    def __init__(
        self,
        broker: BrokerBase,
        db_path: str = DEFAULT_DB_PATH,
    ) -> None:
        self._broker = broker
        self._db_path = Path(db_path).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db: aiosqlite.Connection | None = None
        self._equity_curve: list[dict] = []
        self._migrated = False
        self._loaded = False

    async def _get_db(self) -> aiosqlite.Connection:
        if self._db is None:
            self._db = await aiosqlite.connect(str(self._db_path))
            self._db.row_factory = aiosqlite.Row
            await self._db.execute("PRAGMA journal_mode=WAL")
        return self._db

    async def _ensure_table(self) -> None:
        db = await self._get_db()
        await db.execute("""
            CREATE TABLE IF NOT EXISTS equity_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                cash REAL NOT NULL,
                equity REAL NOT NULL,
                buying_power REAL NOT NULL,
                total_pnl REAL NOT NULL,
                total_pnl_pct REAL NOT NULL,
                position_count INTEGER NOT NULL
            )
        """)
        await db.commit()

    async def _migrate_json(self) -> None:
        """One-time migration from legacy equity_curve.json to SQLite."""
        if self._migrated:
            return
        self._migrated = True

        legacy_path = self._db_path.parent / "equity_curve.json"
        if not legacy_path.exists():
            return

        try:
            data = json.loads(legacy_path.read_text(encoding="utf-8"))
            if not isinstance(data, list) or not data:
                return

            await self._ensure_table()
            db = await self._get_db()
            count = 0
            for entry in data:
                await db.execute(
                    """INSERT OR IGNORE INTO equity_snapshots
                       (timestamp, cash, equity, buying_power, total_pnl, total_pnl_pct, position_count)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        entry.get("timestamp", datetime.now().isoformat()),
                        entry.get("cash", 0.0),
                        entry.get("equity", 0.0),
                        entry.get("buying_power", 0.0),
                        entry.get("total_pnl", 0.0),
                        entry.get("total_pnl_pct", 0.0),
                        entry.get("position_count", 0),
                    ),
                )
                count += 1
            await db.commit()

            # Rename legacy file after successful migration
            legacy_path.rename(legacy_path.with_suffix(".json.migrated"))
            logger.info("Migrated %d equity curve entries from %s", count, legacy_path)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to migrate legacy equity curve: %s", e)

    async def _load_equity_curve(self) -> None:
        """Load equity curve from SQLite into memory."""
        await self._migrate_json()
        await self._ensure_table()
        db = await self._get_db()
        cursor = await db.execute(
            "SELECT * FROM equity_snapshots ORDER BY id ASC"
        )
        rows = await cursor.fetchall()
        self._equity_curve = [
            {
                "timestamp": row["timestamp"],
                "cash": row["cash"],
                "equity": row["equity"],
                "buying_power": row["buying_power"],
                "total_pnl": row["total_pnl"],
                "total_pnl_pct": row["total_pnl_pct"],
                "position_count": row["position_count"],
            }
            for row in rows
        ]
        self._loaded = True

    async def _ensure_loaded(self) -> None:
        if not self._loaded:
            await self._load_equity_curve()

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

        # Persist to SQLite
        await self._ensure_table()
        db = await self._get_db()
        await db.execute(
            """INSERT INTO equity_snapshots
               (timestamp, cash, equity, buying_power, total_pnl, total_pnl_pct, position_count)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                entry["timestamp"], entry["cash"], entry["equity"],
                entry["buying_power"], entry["total_pnl"],
                entry["total_pnl_pct"], entry["position_count"],
            ),
        )
        await db.commit()
        return snapshot

    async def get_equity_curve(self, limit: int | None = None) -> list[dict]:
        """Get historical equity curve entries.

        Args:
            limit: Max number of entries to return (most recent first).

        Returns:
            List of equity curve entries.
        """
        await self._ensure_loaded()
        entries = list(self._equity_curve)
        if limit is not None:
            entries = entries[-limit:]
        return entries

    async def get_stats(self) -> dict:
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

    async def reset(self) -> None:
        """Clear equity curve history (in-memory and SQLite)."""
        self._equity_curve = []
        await self._ensure_table()
        db = await self._get_db()
        await db.execute("DELETE FROM equity_snapshots")
        await db.commit()
        logger.info("Portfolio equity curve reset")

    async def close(self) -> None:
        """Close the database connection."""
        if self._db is not None:
            await self._db.close()
            self._db = None

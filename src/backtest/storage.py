"""Backtest result persistence."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

STORAGE_DIR = Path.home() / ".aegis-trader" / "backtests"


class BacktestStorage:
    """SQLite index + JSON file storage for backtest results."""

    def __init__(self, storage_dir: Path | None = None):
        self._dir = storage_dir or STORAGE_DIR
        self._dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self._dir / "index.db"
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS backtest_runs (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    start_date TEXT,
                    end_date TEXT,
                    initial_capital REAL,
                    final_capital REAL,
                    total_return REAL,
                    max_drawdown REAL,
                    total_trades INTEGER,
                    created_at TEXT NOT NULL
                )
            """)

    def save(self, result: dict) -> str:
        """Save backtest result, return run ID."""
        run_id = uuid4().hex[:12]
        # Write full result to JSON
        result_path = self._dir / f"{run_id}.json"
        result_path.write_text(json.dumps(result, default=str, indent=2))
        # Index in SQLite
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                "INSERT INTO backtest_runs VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    run_id,
                    result["symbol"],
                    result["strategy"],
                    result.get("start_date"),
                    result.get("end_date"),
                    result.get("initial_capital"),
                    result.get("final_capital"),
                    result.get("metrics", {}).get("total_return"),
                    result.get("metrics", {}).get("max_drawdown"),
                    result.get("metrics", {}).get("total_trades"),
                    datetime.now(UTC).isoformat(),
                ),
            )
        return run_id

    def list_runs(self, symbol: str | None = None, limit: int = 50) -> list[dict]:
        """List recent backtest runs, optionally filtered by symbol."""
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            if symbol:
                rows = conn.execute(
                    "SELECT * FROM backtest_runs WHERE symbol = ? ORDER BY created_at DESC LIMIT ?",
                    (symbol.upper(), limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM backtest_runs ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [dict(r) for r in rows]

    def get_run(self, run_id: str) -> dict | None:
        """Get full backtest result by ID."""
        result_path = self._dir / f"{run_id}.json"
        if not result_path.exists():
            return None
        return json.loads(result_path.read_text())

    def delete_run(self, run_id: str) -> bool:
        """Delete a backtest run. Returns True if deleted, False if not found."""
        result_path = self._dir / f"{run_id}.json"
        if not result_path.exists():
            return False
        result_path.unlink()
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("DELETE FROM backtest_runs WHERE id = ?", (run_id,))
        return True

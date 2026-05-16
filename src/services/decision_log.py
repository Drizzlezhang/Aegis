"""Shared append-only decision log manager."""

import asyncio
import sqlite3
from pathlib import Path

from src.config import get_config
from src.models.decision import DecisionEntry, DecisionOutcome


class DecisionLog:
    def __init__(self, storage_path: str | Path | None = None, db_path: str | Path | None = None):
        config = get_config()
        self._db_path = Path(db_path or config.memory.sqlite_path).expanduser()
        self._storage_path = Path(storage_path or "~/.aegis-trader/decisions/").expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._write_lock = asyncio.Lock()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS decisions (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    decision_type TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    actual_pnl REAL,
                    reflection TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_decisions_symbol_ts ON decisions(symbol, timestamp DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_decisions_outcome_ts ON decisions(outcome, timestamp ASC)"
            )
            conn.commit()

    async def append(self, entry: DecisionEntry) -> str:
        async with self._write_lock:
            await asyncio.to_thread(self._append_sqlite, entry)
            self._append_markdown(entry)
        return entry.id

    async def query_by_symbol(self, symbol: str, limit: int = 10) -> list[DecisionEntry]:
        rows = await asyncio.to_thread(self._query_by_symbol_rows, symbol, limit)
        return [DecisionEntry.model_validate_json(row[0]) for row in rows]

    async def query_pending(self) -> list[DecisionEntry]:
        rows = await asyncio.to_thread(self._query_pending_rows)
        return [DecisionEntry.model_validate_json(row[0]) for row in rows]

    async def update_outcome(
        self,
        entry_id: str,
        outcome: DecisionOutcome,
        actual_pnl: float | None = None,
        reflection: str | None = None,
    ) -> None:
        await asyncio.to_thread(self._update_outcome_sqlite, entry_id, outcome, actual_pnl, reflection)

    async def query_recent_reflected(self, limit: int = 5) -> list[DecisionEntry]:
        rows = await asyncio.to_thread(self._query_recent_reflected_rows, limit)
        return [DecisionEntry.model_validate_json(row[0]) for row in rows]

    async def export_markdown(self, symbol: str | None = None) -> str:
        if symbol:
            return await asyncio.to_thread(self._read_markdown_file, self._markdown_path(symbol))

        paths = sorted(self._storage_path.glob("*.md"))
        contents = await asyncio.to_thread(self._read_markdown_files, paths)
        return "\n\n".join(content for content in contents if content)

    def _query_recent_reflected_rows(self, limit: int) -> list[tuple[str]]:
        with sqlite3.connect(str(self._db_path)) as conn:
            return conn.execute(
                "SELECT data_json FROM decisions WHERE outcome != ? ORDER BY timestamp DESC LIMIT ?",
                (DecisionOutcome.PENDING.value, limit),
            ).fetchall()

    def _append_sqlite(self, entry: DecisionEntry) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """
                INSERT INTO decisions (id, timestamp, symbol, decision_type, data_json, outcome, actual_pnl, reflection)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.id,
                    entry.timestamp.isoformat(),
                    entry.symbol.upper(),
                    entry.decision_type.value,
                    entry.model_dump_json(),
                    entry.outcome.value,
                    entry.actual_pnl,
                    entry.reflection,
                ),
            )
            conn.commit()

    def _query_by_symbol_rows(self, symbol: str, limit: int) -> list[tuple[str]]:
        with sqlite3.connect(str(self._db_path)) as conn:
            return conn.execute(
                "SELECT data_json FROM decisions WHERE symbol = ? ORDER BY timestamp DESC LIMIT ?",
                (symbol.upper(), limit),
            ).fetchall()

    def _query_pending_rows(self) -> list[tuple[str]]:
        with sqlite3.connect(str(self._db_path)) as conn:
            return conn.execute(
                "SELECT data_json FROM decisions WHERE outcome = ? ORDER BY timestamp ASC",
                (DecisionOutcome.PENDING.value,),
            ).fetchall()

    def _update_outcome_sqlite(
        self,
        entry_id: str,
        outcome: DecisionOutcome,
        actual_pnl: float | None,
        reflection: str | None,
    ) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            row = conn.execute(
                "SELECT data_json, outcome FROM decisions WHERE id = ?",
                (entry_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"Decision entry not found: {entry_id}")
            if row[1] != DecisionOutcome.PENDING.value:
                raise ValueError(f"Decision outcome already finalized: {entry_id}")

            entry = DecisionEntry.model_validate_json(row[0])
            entry.outcome = outcome
            entry.actual_pnl = actual_pnl
            entry.reflection = reflection
            conn.execute(
                """
                UPDATE decisions
                SET data_json = ?, outcome = ?, actual_pnl = ?, reflection = ?
                WHERE id = ?
                """,
                (
                    entry.model_dump_json(),
                    outcome.value,
                    actual_pnl,
                    reflection,
                    entry_id,
                ),
            )
            conn.commit()

    def _append_markdown(self, entry: DecisionEntry) -> None:
        path = self._markdown_path(entry.symbol)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(self._render_markdown_entry(entry))

    def _read_markdown_file(self, path: Path) -> str:
        return path.read_text() if path.exists() else ""

    def _read_markdown_files(self, paths: list[Path]) -> list[str]:
        return [path.read_text() for path in paths]

    def _markdown_path(self, symbol: str) -> Path:
        return self._storage_path / f"{symbol.upper()}.md"

    def _render_markdown_entry(self, entry: DecisionEntry) -> str:
        lines = [
            f"## {entry.timestamp.isoformat()} | {entry.decision_type.value.upper()}",
            f"- Symbol: {entry.symbol.upper()}",
            f"- Current Price: {entry.current_price}",
            f"- Strategy: {entry.strategy_name or 'n/a'}",
            f"- Contract: {entry.contract_symbol or 'n/a'}",
            f"- Confidence: {entry.confidence}",
            f"- Outcome: {entry.outcome.value}",
            f"- Reasoning: {entry.reasoning or 'n/a'}",
        ]
        if entry.actual_pnl is not None:
            lines.append(f"- Actual PnL: {entry.actual_pnl}")
        if entry.reflection:
            lines.append(f"- Reflection: {entry.reflection}")
        return "\n".join(lines) + "\n\n"

"""Database storage operations for Aegis-Memory Agent."""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from src.models import AgentState

logger = logging.getLogger(__name__)


class AnalysisStorage:
    """SQLite storage for analysis results and trading history."""

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._initialized = False

    def ensure_schema(self) -> None:
        """Ensure database schema exists."""
        if self._initialized:
            return

        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    trade_date TEXT NOT NULL,
                    agent_sequence TEXT,
                    ohlcv_summary TEXT,
                    options_summary TEXT,
                    support_levels TEXT,
                    resistance_levels TEXT,
                    valuation_summary TEXT,
                    recommendations TEXT,
                    action_report TEXT,
                    execution_time REAL DEFAULT 0,
                    success INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS trading_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    action_date TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    contract_symbol TEXT,
                    strike REAL,
                    expiry TEXT,
                    option_type TEXT,
                    quantity INTEGER,
                    entry_price REAL,
                    exit_price REAL,
                    pnl REAL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS market_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    note_date TEXT NOT NULL,
                    category TEXT,
                    content TEXT NOT NULL,
                    tags TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()

        self._initialized = True

    def record_analysis(
        self, state: AgentState, execution_time: float = 0.0, success: bool = True
    ) -> int:
        """Record analysis result to database. Returns inserted row id."""
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                ohlcv_summary = None
                if state.ohlcv_data:
                    latest = state.ohlcv_data[-1] if state.ohlcv_data else None
                    if latest:
                        ohlcv_summary = json.dumps({
                            "latest_close": latest.close,
                            "latest_volume": latest.volume,
                            "data_points": len(state.ohlcv_data)
                        })

                options_summary = None
                if state.options_chain:
                    options_summary = json.dumps({
                        "spot_price": state.options_chain.spot_price,
                        "calls_count": len(state.options_chain.calls),
                        "puts_count": len(state.options_chain.puts),
                        "expiry_dates": [str(d) for d in state.options_chain.expiry_dates]
                    })

                support_levels = json.dumps([
                    {"price": s.price, "confidence": s.confidence, "source": s.source}
                    for s in state.support_levels
                ]) if state.support_levels else None

                resistance_levels = json.dumps([
                    {"price": r.price, "confidence": r.confidence, "source": r.source}
                    for r in state.resistance_levels
                ]) if state.resistance_levels else None

                valuation_summary = None
                if state.valuation_range:
                    valuation_summary = json.dumps({
                        "current_price": state.valuation_range.current_price,
                        "fair_estimate": state.valuation_range.fair_estimate,
                        "discount_to_fair": state.valuation_range.discount_to_fair,
                        "is_undervalued": state.valuation_range.is_undervalued
                    })

                recommendations = json.dumps([
                    {
                        "type": r.recommendation_type,
                        "strike": r.contract.strike,
                        "expiry": str(r.contract.expiry),
                        "entry_price": r.entry_price,
                        "confidence": r.confidence
                    }
                    for r in state.recommended_options
                ]) if state.recommended_options else None

                cursor = conn.execute("""
                    INSERT INTO analysis_results (
                        symbol, trade_date, agent_sequence, ohlcv_summary,
                        options_summary, support_levels, resistance_levels,
                        valuation_summary, recommendations, action_report,
                        execution_time, success
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    state.symbol,
                    str(state.trade_date),
                    json.dumps(state.agent_sequence),
                    ohlcv_summary,
                    options_summary,
                    support_levels,
                    resistance_levels,
                    valuation_summary,
                    recommendations,
                    state.action_report,
                    execution_time,
                    1 if success else 0,
                ))

                conn.commit()
                row_id = cursor.lastrowid or 0
                logger.info(f"Analysis recorded for {state.symbol} (id={row_id})")
                return row_id

        except Exception as e:
            logger.error(f"Error recording analysis: {e}")
            return 0

    def get_analysis_history(
        self, symbol: str | None = None, limit: int = 20, offset: int = 0
    ) -> list[dict[str, Any]]:
        """Get analysis history from database."""
        self.ensure_schema()
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.row_factory = sqlite3.Row
                if symbol:
                    rows = conn.execute(
                        """SELECT id, symbol, trade_date, agent_sequence,
                           recommendations, execution_time, success, created_at
                           FROM analysis_results
                           WHERE symbol = ?
                           ORDER BY created_at DESC
                           LIMIT ? OFFSET ?""",
                        (symbol.upper(), limit, offset),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """SELECT id, symbol, trade_date, agent_sequence,
                           recommendations, execution_time, success, created_at
                           FROM analysis_results
                           ORDER BY created_at DESC
                           LIMIT ? OFFSET ?""",
                        (limit, offset),
                    ).fetchall()

                results = []
                for row in rows:
                    recs = json.loads(row["recommendations"] or "[]")
                    agent_seq = json.loads(row["agent_sequence"] or "[]")
                    results.append({
                        "id": row["id"],
                        "symbol": row["symbol"],
                        "tradeDate": row["trade_date"],
                        "agentSequence": agent_seq,
                        "recommendationsCount": len(recs),
                        "executionTime": row["execution_time"] or 0.0,
                        "success": bool(row["success"]),
                    })
                return results
        except Exception as e:
            logger.error(f"Error fetching analysis history: {e}")
            return []

    def get_analysis_by_id(self, analysis_id: int) -> dict[str, Any] | None:
        """Get a single analysis record by id."""
        self.ensure_schema()
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    """SELECT * FROM analysis_results WHERE id = ?""",
                    (analysis_id,),
                ).fetchone()

                if not row:
                    return None

                return {
                    "id": row["id"],
                    "symbol": row["symbol"],
                    "tradeDate": row["trade_date"],
                    "agentSequence": json.loads(row["agent_sequence"] or "[]"),
                    "ohlcvSummary": json.loads(row["ohlcv_summary"] or "null"),
                    "optionsSummary": json.loads(row["options_summary"] or "null"),
                    "supportLevels": json.loads(row["support_levels"] or "[]"),
                    "resistanceLevels": json.loads(row["resistance_levels"] or "[]"),
                    "valuationSummary": json.loads(row["valuation_summary"] or "null"),
                    "recommendations": json.loads(row["recommendations"] or "[]"),
                    "actionReport": row["action_report"],
                    "executionTime": row["execution_time"] or 0.0,
                    "success": bool(row["success"]),
                    "createdAt": row["created_at"],
                }
        except Exception as e:
            logger.error(f"Error fetching analysis by id: {e}")
            return None

"""Database query operations for Aegis-Memory Agent."""

from typing import Dict, List, Any, Optional
import logging
import json
import sqlite3
from datetime import date

logger = logging.getLogger(__name__)


async def recall_recent_analysis(conn_path: str, symbol: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Recall recent analysis results for a symbol."""
    try:
        with sqlite3.connect(conn_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM analysis_results
                WHERE symbol = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (symbol.upper(), limit))

            rows = cursor.fetchall()
            results = []
            json_fields = ["ohlcv_summary", "options_summary", "support_levels",
                           "resistance_levels", "valuation_summary", "recommendations", "agent_sequence"]
            for row in rows:
                result = dict(row)
                for field in json_fields:
                    if result.get(field):
                        try:
                            result[field] = json.loads(result[field])
                        except (json.JSONDecodeError, TypeError):
                            pass
                results.append(result)
            return results
    except Exception as e:
        logger.error(f"Error recalling analysis for {symbol}: {e}")
        return []


async def recall_trading_actions(conn_path: str, symbol: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """Recall trading actions."""
    try:
        with sqlite3.connect(conn_path) as conn:
            conn.row_factory = sqlite3.Row
            if symbol:
                cursor = conn.execute("""
                    SELECT * FROM trading_actions
                    WHERE symbol = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (symbol.upper(), limit))
            else:
                cursor = conn.execute("""
                    SELECT * FROM trading_actions
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error recalling trading actions: {e}")
        return []


async def add_trading_action(conn_path: str, action: Dict[str, Any]) -> bool:
    """Add a trading action record."""
    try:
        with sqlite3.connect(conn_path) as conn:
            conn.execute("""
                INSERT INTO trading_actions (
                    symbol, action_date, action_type, contract_symbol,
                    strike, expiry, option_type, quantity, entry_price,
                    exit_price, pnl, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                action.get("symbol", "").upper(),
                str(action.get("action_date", date.today())),
                action.get("action_type", ""),
                action.get("contract_symbol", ""),
                action.get("strike"),
                str(action.get("expiry")) if action.get("expiry") else None,
                action.get("option_type", ""),
                action.get("quantity", 0),
                action.get("entry_price"),
                action.get("exit_price"),
                action.get("pnl"),
                action.get("notes", "")
            ))
            conn.commit()
            logger.info(f"Trading action recorded: {action.get('action_type')} {action.get('symbol')}")
            return True
    except Exception as e:
        logger.error(f"Error adding trading action: {e}")
        return False


async def add_market_note(conn_path: str, note: Dict[str, Any]) -> bool:
    """Add a market note."""
    try:
        with sqlite3.connect(conn_path) as conn:
            conn.execute("""
                INSERT INTO market_notes (symbol, note_date, category, content, tags)
                VALUES (?, ?, ?, ?, ?)
            """, (
                note.get("symbol", "").upper() if note.get("symbol") else None,
                str(note.get("note_date", date.today())),
                note.get("category", "general"),
                note.get("content", ""),
                json.dumps(note.get("tags", [])) if note.get("tags") else None
            ))
            conn.commit()
            logger.info("Market note recorded")
            return True
    except Exception as e:
        logger.error(f"Error adding market note: {e}")
        return False


async def recall_market_notes(
    conn_path: str, symbol: Optional[str] = None, category: Optional[str] = None, limit: int = 10
) -> List[Dict[str, Any]]:
    """Recall market notes."""
    try:
        with sqlite3.connect(conn_path) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM market_notes WHERE 1=1"
            params = []

            if symbol:
                query += " AND symbol = ?"
                params.append(symbol.upper())
            if category:
                query += " AND category = ?"
                params.append(category)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            results = []
            for row in rows:
                result = dict(row)
                if result.get("tags"):
                    try:
                        result["tags"] = json.loads(result["tags"])
                    except (json.JSONDecodeError, TypeError):
                        result["tags"] = []
                results.append(result)
            return results
    except Exception as e:
        logger.error(f"Error recalling market notes: {e}")
        return []

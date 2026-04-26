"""Aegis-Memory Agent implementation."""

import logging
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.agents.base import BaseAgent
from src.config import get_config
from src.models import AgentState

from . import queries
from .storage import AnalysisStorage

if TYPE_CHECKING:
    from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class AegisMemoryAgent(BaseAgent):
    """Aegis-Memory Agent: Records and retrieves trading analysis history with vector storage."""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(
            name="Aegis-Memory",
            description="Records trading analysis results and provides historical recall with semantic search",
            config=config or {}
        )
        self._config = get_config()
        self._db_path = Path(self._config.memory.sqlite_path).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._storage = AnalysisStorage(self._db_path)
        self._vector_store: VectorStore | None = None

    async def initialize(self) -> None:
        """Initialize database schema and vector store."""
        self._storage.ensure_schema()

        # Initialize vector store
        try:
            from .vector_store import VectorStore

            self._vector_store = VectorStore()
            logger.info("Vector store initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize vector store: {e}. Semantic search will be disabled.")
            self._vector_store = None

        logger.info(f"Aegis-Memory database initialized at {self._db_path}")

    async def run(self, state: AgentState) -> AgentState:
        """Record analysis results to memory with vector storage."""
        symbol = state.symbol.upper()
        logger.info(f"Aegis-Memory recording analysis for symbol: {symbol}")

        state.add_agent_step(self.name)

        # Record to SQLite
        self._storage.record_analysis(state)

        # Also record to vector store if available
        if self._vector_store:
            await self._add_analysis_to_vector_store(state)

        logger.info(f"Aegis-Memory completed recording for symbol: {symbol}")
        return state

    async def _add_analysis_to_vector_store(self, state: AgentState) -> None:
        """Add analysis to vector store for semantic search."""
        assert self._vector_store is not None  # noqa: S101
        try:
            # Get the latest analysis ID from SQLite
            with sqlite3.connect(str(self._db_path)) as conn:
                cursor = conn.execute(
                    "SELECT id FROM analysis_results WHERE symbol = ? ORDER BY id DESC LIMIT 1",
                    (state.symbol,)
                )
                result = cursor.fetchone()
                if result:
                    analysis_id = result[0]

                    # Prepare analysis data for vector store
                    analysis_data = {
                        "symbol": state.symbol,
                        "trade_date": str(state.trade_date),
                        "action_report": state.action_report,
                        "support_levels": [
                            {"price": s.price, "confidence": s.confidence, "source": s.source}
                            for s in state.support_levels
                        ] if state.support_levels else [],
                        "resistance_levels": [
                            {"price": r.price, "confidence": r.confidence, "source": r.source}
                            for r in state.resistance_levels
                        ] if state.resistance_levels else [],
                        "valuation_summary": {
                            "current_price": state.valuation_range.current_price,
                            "fair_estimate": state.valuation_range.fair_estimate,
                            "discount_to_fair": state.valuation_range.discount_to_fair,
                            "is_undervalued": state.valuation_range.is_undervalued
                        } if state.valuation_range else {},
                        "recommendations": [
                            {
                                "type": r.recommendation_type,
                                "strike": r.contract.strike,
                                "expiry": str(r.contract.expiry),
                                "entry_price": r.entry_price,
                                "confidence": r.confidence
                            }
                            for r in state.recommended_options
                        ] if state.recommended_options else []
                    }

                    # Add to vector store
                    self._vector_store.add_analysis(analysis_id, analysis_data)
                    logger.debug(f"Analysis {analysis_id} added to vector store")

        except Exception as e:
            logger.error(f"Error adding analysis to vector store: {e}")

    async def recall_recent_analysis(self, symbol: str, limit: int = 5) -> list[dict[str, Any]]:
        """Recall recent analysis results for a symbol."""
        return await queries.recall_recent_analysis(str(self._db_path), symbol, limit)

    async def search_analysis_semantic(self, query: str, symbol: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
        """Search analysis results by semantic similarity."""
        if not self._vector_store:
            logger.warning("Vector store not available for semantic search")
            return []

        # Perform semantic search
        vector_results = self._vector_store.search_analysis(query, symbol, limit)

        # Get full details from SQLite
        full_results = []
        for vec_result in vector_results:
            analysis_id = vec_result["id"]
            try:
                # Get full analysis details from SQLite
                with sqlite3.connect(str(self._db_path)) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute(
                        "SELECT * FROM analysis_results WHERE id = ?",
                        (analysis_id,)
                    )
                    row = cursor.fetchone()
                    if row:
                        result = dict(row)
                        # Add vector search metadata
                        result["vector_metadata"] = {
                            "document": vec_result["document"],
                            "similarity_score": 1.0 - vec_result["distance"],  # Convert distance to similarity
                            "distance": vec_result["distance"]
                        }
                        full_results.append(result)
            except Exception as e:
                logger.error(f"Error fetching analysis {analysis_id}: {e}")

        return full_results

    async def recall_trading_actions(self, symbol: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        """Recall trading actions."""
        return await queries.recall_trading_actions(str(self._db_path), symbol, limit)

    async def add_trading_action(self, action: dict[str, Any]) -> bool:
        """Add a trading action record."""
        success = await queries.add_trading_action(str(self._db_path), action)

        # Also add to vector store if available
        if success and self._vector_store:
            try:
                # Get the latest action ID
                with sqlite3.connect(str(self._db_path)) as conn:
                    cursor = conn.execute(
                        "SELECT id FROM trading_actions ORDER BY id DESC LIMIT 1"
                    )
                    result = cursor.fetchone()
                    if result:
                        action_id = result[0]
                        self._vector_store.add_trading_action(action_id, action)
            except Exception as e:
                logger.error(f"Error adding trading action to vector store: {e}")

        return success

    async def add_market_note(self, note: dict[str, Any]) -> bool:
        """Add a market note."""
        success = await queries.add_market_note(str(self._db_path), note)

        # Also add to vector store if available
        if success and self._vector_store:
            try:
                # Get the latest note ID
                with sqlite3.connect(str(self._db_path)) as conn:
                    cursor = conn.execute(
                        "SELECT id FROM market_notes ORDER BY id DESC LIMIT 1"
                    )
                    result = cursor.fetchone()
                    if result:
                        note_id = result[0]
                        self._vector_store.add_market_note(note_id, note)
            except Exception as e:
                logger.error(f"Error adding market note to vector store: {e}")

        return success

    async def recall_market_notes(
        self, symbol: str | None = None, category: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Recall market notes."""
        return await queries.recall_market_notes(str(self._db_path), symbol, category, limit)

    async def search_market_notes_semantic(
        self, query: str, symbol: str | None = None, category: str | None = None, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Search market notes by semantic similarity."""
        if not self._vector_store:
            logger.warning("Vector store not available for semantic search")
            return []

        # Perform semantic search
        vector_results = self._vector_store.search_market_notes(query, symbol, category, limit)

        # Get full details from SQLite
        full_results = []
        for vec_result in vector_results:
            note_id = vec_result["id"]
            try:
                # Get full note details from SQLite
                with sqlite3.connect(str(self._db_path)) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute(
                        "SELECT * FROM market_notes WHERE id = ?",
                        (note_id,)
                    )
                    row = cursor.fetchone()
                    if row:
                        result = dict(row)
                        # Add vector search metadata
                        result["vector_metadata"] = {
                            "document": vec_result["document"],
                            "similarity_score": 1.0 - vec_result["distance"],
                            "distance": vec_result["distance"]
                        }
                        full_results.append(result)
            except Exception as e:
                logger.error(f"Error fetching market note {note_id}: {e}")

        return full_results

    async def search_trading_actions_semantic(
        self, query: str, symbol: str | None = None, action_type: str | None = None, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Search trading actions by semantic similarity."""
        if not self._vector_store:
            logger.warning("Vector store not available for semantic search")
            return []

        # Perform semantic search
        vector_results = self._vector_store.search_trading_actions(query, symbol, action_type, limit)

        # Get full details from SQLite
        full_results = []
        for vec_result in vector_results:
            action_id = vec_result["id"]
            try:
                # Get full action details from SQLite
                with sqlite3.connect(str(self._db_path)) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute(
                        "SELECT * FROM trading_actions WHERE id = ?",
                        (action_id,)
                    )
                    row = cursor.fetchone()
                    if row:
                        result = dict(row)
                        # Add vector search metadata
                        result["vector_metadata"] = {
                            "document": vec_result["document"],
                            "similarity_score": 1.0 - vec_result["distance"],
                            "distance": vec_result["distance"]
                        }
                        full_results.append(result)
            except Exception as e:
                logger.error(f"Error fetching trading action {action_id}: {e}")

        return full_results

    async def get_vector_store_stats(self) -> dict[str, Any]:
        """Get vector store statistics."""
        if not self._vector_store:
            return {"error": "Vector store not available"}

        return self._vector_store.get_stats()

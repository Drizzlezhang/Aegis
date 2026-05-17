"""Aegis-Memory Agent implementation."""

import logging
import re
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from src.agents.base import BaseAgent
from src.agents.position_monitor.position_bridge import PositionBridge
from src.agents.position_monitor.position_manager import PositionManager
from src.config import get_config
from src.models import AgentState, DecisionEntry, DecisionType

from . import queries
from .decision_log import DecisionLog
from .storage import AnalysisStorage

try:
    from .vector_store import VectorStore
except ImportError:
    VectorStore = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from .vector_store import VectorStore as VectorStoreType

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
        self._decision_log = DecisionLog(db_path=self._db_path)
        position_storage_path = self.config.get("position_storage_path", "~/.aegis-trader/positions.json")
        self._position_manager = PositionManager(storage_path=position_storage_path)
        self._position_bridge = PositionBridge(self._position_manager)
        self._vector_store: VectorStoreType | None = None

    async def initialize(self) -> None:
        """Initialize database schema and vector store."""
        self._storage.ensure_schema()
        await self._position_manager.load()

        # Initialize vector store
        try:
            if VectorStore is None:
                from .vector_store import VectorStore as vector_store_class
            else:
                vector_store_class = VectorStore
            self._vector_store = vector_store_class()
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

        await self.log_decision(state)

        # 新增：查找相似决策
        similar = await self.find_similar_decisions(state)
        if similar:
            state.metadata["similar_decisions"] = similar

        reflection_feedback = state.metadata.get("reflection_feedback", [])
        for feedback in reflection_feedback:
            await self._store_reflection(feedback)

        logger.info(f"Aegis-Memory completed recording for symbol: {symbol}")
        return state

    async def log_decision(self, state: AgentState) -> None:
        current_price = 0.0
        if state.options_chain:
            current_price = state.options_chain.spot_price
        elif state.ohlcv_data:
            current_price = state.ohlcv_data[-1].close

        technical_score = self._extract_technical_score(state.analysis_report)
        macro_regime = self._extract_macro_regime(state.analysis_report)

        if not state.recommended_options:
            await self._decision_log.append(
                DecisionEntry(
                    id=str(uuid4()),
                    symbol=state.symbol,
                    decision_type=DecisionType.SKIP,
                    current_price=current_price,
                    technical_score=technical_score,
                    macro_regime=macro_regime,
                    confidence=0.0,
                    reasoning="No recommendation from analysis pipeline",
                )
            )
            return

        for option in state.recommended_options:
            entry = DecisionEntry(
                id=str(uuid4()),
                symbol=state.symbol,
                decision_type=DecisionType.OPEN,
                current_price=current_price,
                technical_score=technical_score,
                macro_regime=macro_regime,
                strategy_name=option.recommendation_type,
                confidence=option.confidence,
                reasoning=option.reasoning,
                contract_symbol=option.contract.contract_symbol,
                entry_price=option.entry_price,
                stop_loss=option.stop_loss,
                profit_target=option.target_price,
                quantity=1,
            )
            await self._decision_log.append(entry)
            try:
                await self._position_bridge.bridge_open_decision(entry)
            except Exception as exc:
                logger.warning("Position bridge failed for %s: %s", entry.id, exc)

    async def _store_reflection(self, feedback: dict) -> None:
        if not self._vector_store:
            return
        text = (
            f"Decision reflection for {feedback['symbol']}: "
            f"{feedback['decision_type']} resulted in {feedback['outcome']}. "
            f"PnL: {feedback.get('pnl', 'N/A')}. "
            f"Lesson: {feedback.get('reflection', 'No reflection recorded.')}"
        )
        try:
            self._vector_store.add_memory(
                text=text,
                metadata={
                    "type": "decision_reflection",
                    "symbol": feedback["symbol"],
                    "outcome": feedback["outcome"],
                    "timestamp": feedback["timestamp"],
                },
            )
        except Exception as exc:
            logger.warning("Failed to store reflection for %s: %s", feedback["symbol"], exc)

    def _extract_technical_score(self, analysis_report: str) -> float | None:
        match = re.search(r"technical[_\s-]*score\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)", analysis_report, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return None

    def _extract_macro_regime(self, analysis_report: str) -> str | None:
        match = re.search(r"macro[_\s-]*regime\s*[:=]\s*([^\n,;]+)", analysis_report, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

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

    async def find_similar_decisions(self, state: AgentState) -> list[dict]:
        """查找与当前分析情境相似的历史决策。
        
        相似性维度:
        1. 相同 symbol
        2. 类似技术 grade
        3. 类似宏观 regime
        4. 类似 debate verdict
        
        返回最相关的 5 条历史决策及其结果。
        """
        if not self._vector_store:
            return []

        technical_grade = state.metadata.get("technical_grade", "")
        macro_regime = state.metadata.get("macro_regime", "")
        query = f"Decision for {state.symbol}: grade={technical_grade}, regime={macro_regime}"
        try:
            memories = self._vector_store.search(query, top_k=10)
        except Exception as exc:
            logger.warning("find_similar_decisions search failed: %s", exc)
            return []

        # 过滤出 decision_reflection 类型的 memory
        relevant = [m for m in memories if m.get("metadata", {}).get("type") == "decision_reflection"]
        return relevant[:5]

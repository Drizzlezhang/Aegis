"""Vector storage for semantic search and similarity retrieval."""

import logging
from pathlib import Path
from typing import Any

try:
    import chromadb
    from chromadb.config import Settings
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    raise ImportError(
        "Vector store dependencies not installed. "
        "Run: pip install chromadb sentence-transformers"
    ) from e

from src.config import get_config

logger = logging.getLogger(__name__)


class VectorStore:
    """Vector storage for semantic search and similarity retrieval."""

    def __init__(self, db_path: Path | None = None):
        """Initialize vector store."""
        config = get_config()

        # Determine storage path
        if db_path:
            self._db_path = db_path
        else:
            base_path = Path(config.memory.sqlite_path).expanduser().parent
            self._db_path = base_path / "vector_store"

        self._db_path.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB
        self._client = chromadb.PersistentClient(
            path=str(self._db_path),
            settings=Settings(anonymized_telemetry=False)
        )

        # Initialize embedding model
        self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self._embedding_dimension = 384  # all-MiniLM-L6-v2 output dimension

        # Initialize collections
        self._analysis_collection = self._client.get_or_create_collection(
            name="analysis_results",
            metadata={"description": "Analysis results with semantic search"}
        )
        self._notes_collection = self._client.get_or_create_collection(
            name="market_notes",
            metadata={"description": "Market notes with semantic search"}
        )
        self._actions_collection = self._client.get_or_create_collection(
            name="trading_actions",
            metadata={"description": "Trading actions with semantic search"}
        )

        logger.info(f"Vector store initialized at {self._db_path}")

    def _generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for text."""
        if not text:
            return [0.0] * self._embedding_dimension

        # Generate embedding
        embedding = self._embedding_model.encode(text)
        return list(embedding.tolist())

    def _prepare_analysis_document(self, analysis_data: dict[str, Any]) -> str:
        """Prepare analysis data for embedding."""
        parts = []

        # Symbol and date
        parts.append(f"Symbol: {analysis_data.get('symbol', '')}")
        parts.append(f"Date: {analysis_data.get('trade_date', '')}")

        # Action report
        if analysis_data.get('action_report'):
            parts.append(f"Analysis: {analysis_data['action_report']}")

        # Support levels
        support_levels = analysis_data.get('support_levels', [])
        if support_levels:
            support_text = ", ".join([f"${s.get('price', 0)}" for s in support_levels])
            parts.append(f"Support levels: {support_text}")

        # Resistance levels
        resistance_levels = analysis_data.get('resistance_levels', [])
        if resistance_levels:
            resistance_text = ", ".join([f"${r.get('price', 0)}" for r in resistance_levels])
            parts.append(f"Resistance levels: {resistance_text}")

        # Valuation summary
        valuation = analysis_data.get('valuation_summary', {})
        if valuation:
            parts.append(f"Valuation: current ${valuation.get('current_price', 0)}, "
                        f"fair ${valuation.get('fair_estimate', 0)}")

        # Recommendations
        recommendations = analysis_data.get('recommendations', [])
        if recommendations:
            rec_texts = []
            for rec in recommendations:
                rec_texts.append(f"{rec.get('type', '')} at ${rec.get('strike', 0)}")
            parts.append(f"Recommendations: {', '.join(rec_texts)}")

        return " | ".join(parts)

    def _prepare_note_document(self, note_data: dict[str, Any]) -> str:
        """Prepare market note for embedding."""
        parts = []

        if note_data.get('symbol'):
            parts.append(f"Symbol: {note_data['symbol']}")

        if note_data.get('category'):
            parts.append(f"Category: {note_data['category']}")

        if note_data.get('content'):
            parts.append(f"Note: {note_data['content']}")

        if note_data.get('tags'):
            tags = note_data['tags']
            if isinstance(tags, list):
                parts.append(f"Tags: {', '.join(tags)}")

        return " | ".join(parts)

    def _prepare_action_document(self, action_data: dict[str, Any]) -> str:
        """Prepare trading action for embedding."""
        parts = []

        if action_data.get('symbol'):
            parts.append(f"Symbol: {action_data['symbol']}")

        if action_data.get('action_type'):
            parts.append(f"Action: {action_data['action_type']}")

        if action_data.get('contract_symbol'):
            parts.append(f"Contract: {action_data['contract_symbol']}")

        if action_data.get('strike'):
            parts.append(f"Strike: ${action_data['strike']}")

        if action_data.get('option_type'):
            parts.append(f"Option type: {action_data['option_type']}")

        if action_data.get('notes'):
            parts.append(f"Notes: {action_data['notes']}")

        return " | ".join(parts)

    def add_analysis(self, analysis_id: int, analysis_data: dict[str, Any]) -> bool:
        """Add analysis result to vector store."""
        try:
            # Prepare document for embedding
            document = self._prepare_analysis_document(analysis_data)

            # Generate embedding
            embedding = self._generate_embedding(document)

            # Add to collection
            self._analysis_collection.add(
                embeddings=[embedding],
                documents=[document],
                metadatas=[{
                    "id": analysis_id,
                    "symbol": analysis_data.get('symbol', ''),
                    "trade_date": analysis_data.get('trade_date', ''),
                    "type": "analysis"
                }],
                ids=[f"analysis_{analysis_id}"]
            )

            logger.debug(f"Analysis {analysis_id} added to vector store")
            return True

        except Exception as e:
            logger.error(f"Error adding analysis to vector store: {e}")
            return False

    def add_memory(self, text: str, metadata: dict[str, Any]) -> bool:
        """Add a generic memory entry to vector store."""
        try:
            embedding = self._generate_embedding(text)
            memory_id = f"memory_{metadata.get('timestamp', '')}_{metadata.get('symbol', '')}"
            self._notes_collection.add(
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata],
                ids=[memory_id]
            )
            logger.debug("Memory entry added to vector store")
            return True
        except Exception as e:
            logger.error(f"Error adding memory to vector store: {e}")
            return False

    def add_market_note(self, note_id: int, note_data: dict[str, Any]) -> bool:
        """Add market note to vector store."""
        try:
            # Prepare document for embedding
            document = self._prepare_note_document(note_data)

            # Generate embedding
            embedding = self._generate_embedding(document)

            # Add to collection
            self._notes_collection.add(
                embeddings=[embedding],
                documents=[document],
                metadatas=[{
                    "id": note_id,
                    "symbol": note_data.get('symbol', ''),
                    "category": note_data.get('category', 'general'),
                    "type": "note"
                }],
                ids=[f"note_{note_id}"]
            )

            logger.debug(f"Market note {note_id} added to vector store")
            return True

        except Exception as e:
            logger.error(f"Error adding market note to vector store: {e}")
            return False

    def add_trading_action(self, action_id: int, action_data: dict[str, Any]) -> bool:
        """Add trading action to vector store."""
        try:
            # Prepare document for embedding
            document = self._prepare_action_document(action_data)

            # Generate embedding
            embedding = self._generate_embedding(document)

            # Add to collection
            self._actions_collection.add(
                embeddings=[embedding],
                documents=[document],
                metadatas=[{
                    "id": action_id,
                    "symbol": action_data.get('symbol', ''),
                    "action_type": action_data.get('action_type', ''),
                    "type": "action"
                }],
                ids=[f"action_{action_id}"]
            )

            logger.debug(f"Trading action {action_id} added to vector store")
            return True

        except Exception as e:
            logger.error(f"Error adding trading action to vector store: {e}")
            return False

    def search_analysis(self, query: str, symbol: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
        """Search analysis results by semantic similarity."""
        try:
            # Generate query embedding
            query_embedding = self._generate_embedding(query)

            # Build where filter
            where_filter = {"type": "analysis"}
            if symbol:
                where_filter["symbol"] = symbol.upper()

            # ChromaDB expects a single operator for where clause
            # Convert to proper query format
            where_clause: dict[str, Any] = {"type": "analysis"}
            if symbol:
                where_clause = {"$and": [{"type": "analysis"}, {"symbol": symbol.upper()}]}

            # Search in collection
            results = self._analysis_collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_clause
            )

            # Format results
            formatted_results = []
            if results['ids'] and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        "id": int(results['ids'][0][i].split('_')[1]),
                        "document": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "distance": results['distances'][0][i]
                    })

            return formatted_results

        except Exception as e:
            logger.error(f"Error searching analysis: {e}")
            return []

    def search_market_notes(self, query: str, symbol: str | None = None,
                           category: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
        """Search market notes by semantic similarity."""
        try:
            # Generate query embedding
            query_embedding = self._generate_embedding(query)

            # Build where filter
            where_filter = {"type": "note"}
            if symbol:
                where_filter["symbol"] = symbol.upper()
            if category:
                where_filter["category"] = category

            # Convert to proper query format
            where_clause: dict[str, Any] = {"type": "note"}
            if symbol and category:
                where_clause = {"$and": [{"type": "note"}, {"symbol": symbol.upper()}, {"category": category}]}
            elif symbol:
                where_clause = {"$and": [{"type": "note"}, {"symbol": symbol.upper()}]}
            elif category:
                where_clause = {"$and": [{"type": "note"}, {"category": category}]}

            # Search in collection
            results = self._notes_collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_clause
            )

            # Format results
            formatted_results = []
            if results['ids'] and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        "id": int(results['ids'][0][i].split('_')[1]),
                        "document": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "distance": results['distances'][0][i]
                    })

            return formatted_results

        except Exception as e:
            logger.error(f"Error searching market notes: {e}")
            return []

    def search_trading_actions(self, query: str, symbol: str | None = None,
                              action_type: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
        """Search trading actions by semantic similarity."""
        try:
            # Generate query embedding
            query_embedding = self._generate_embedding(query)

            # Build where filter
            where_filter = {"type": "action"}
            if symbol:
                where_filter["symbol"] = symbol.upper()
            if action_type:
                where_filter["action_type"] = action_type

            # Convert to proper query format
            where_clause: dict[str, Any] = {"type": "action"}
            if symbol and action_type:
                where_clause = {"$and": [{"type": "action"}, {"symbol": symbol.upper()}, {"action_type": action_type}]}
            elif symbol:
                where_clause = {"$and": [{"type": "action"}, {"symbol": symbol.upper()}]}
            elif action_type:
                where_clause = {"$and": [{"type": "action"}, {"action_type": action_type}]}

            # Search in collection
            results = self._actions_collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_clause
            )

            # Format results
            formatted_results = []
            if results['ids'] and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        "id": int(results['ids'][0][i].split('_')[1]),
                        "document": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "distance": results['distances'][0][i]
                    })

            return formatted_results

        except Exception as e:
            logger.error(f"Error searching trading actions: {e}")
            return []

    def delete_analysis(self, analysis_id: int) -> bool:
        """Delete analysis from vector store."""
        try:
            self._analysis_collection.delete(ids=[f"analysis_{analysis_id}"])
            logger.debug(f"Analysis {analysis_id} deleted from vector store")
            return True
        except Exception as e:
            logger.error(f"Error deleting analysis from vector store: {e}")
            return False

    def delete_market_note(self, note_id: int) -> bool:
        """Delete market note from vector store."""
        try:
            self._notes_collection.delete(ids=[f"note_{note_id}"])
            logger.debug(f"Market note {note_id} deleted from vector store")
            return True
        except Exception as e:
            logger.error(f"Error deleting market note from vector store: {e}")
            return False

    def delete_trading_action(self, action_id: int) -> bool:
        """Delete trading action from vector store."""
        try:
            self._actions_collection.delete(ids=[f"action_{action_id}"])
            logger.debug(f"Trading action {action_id} deleted from vector store")
            return True
        except Exception as e:
            logger.error(f"Error deleting trading action from vector store: {e}")
            return False

    def get_stats(self) -> dict[str, Any]:
        """Get vector store statistics."""
        try:
            analysis_count = self._analysis_collection.count()
            notes_count = self._notes_collection.count()
            actions_count = self._actions_collection.count()

            return {
                "analysis_results": analysis_count,
                "market_notes": notes_count,
                "trading_actions": actions_count,
                "total": analysis_count + notes_count + actions_count,
                "embedding_dimension": self._embedding_dimension,
                "storage_path": str(self._db_path)
            }
        except Exception as e:
            logger.error(f"Error getting vector store stats: {e}")
            return {}

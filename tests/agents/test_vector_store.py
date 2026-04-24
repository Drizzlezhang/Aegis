"""Tests for vector storage functionality."""

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.aegis_memory.vector_store import VectorStore


class TestVectorStore:
    """Test vector storage functionality."""

    @pytest.fixture
    def temp_vector_dir(self):
        """Create temporary directory for vector store."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def vector_store(self, temp_vector_dir):
        """Create vector store instance."""
        # Skip test if dependencies not installed
        try:
            store = VectorStore(temp_vector_dir)
            return store
        except ImportError as e:
            pytest.skip(f"Skipping vector store test: {e}")

    def test_initialization(self, vector_store, temp_vector_dir):
        """Test vector store initialization."""
        assert vector_store is not None
        assert vector_store._db_path == temp_vector_dir
        assert vector_store._client is not None
        assert vector_store._embedding_model is not None

    def test_generate_embedding(self, vector_store):
        """Test embedding generation."""
        text = "Test text for embedding"
        embedding = vector_store._generate_embedding(text)

        assert isinstance(embedding, list)
        assert len(embedding) == 384  # all-MiniLM-L6-v2 dimension
        assert all(isinstance(x, float) for x in embedding)

    def test_prepare_analysis_document(self, vector_store):
        """Test analysis document preparation."""
        analysis_data = {
            "symbol": "QQQ",
            "trade_date": "2024-01-10",
            "action_report": "Strong bullish momentum with clear support",
            "support_levels": [
                {"price": 95.0, "confidence": 0.8, "source": "volume_profile"},
                {"price": 98.5, "confidence": 0.7, "source": "fibonacci"}
            ],
            "resistance_levels": [
                {"price": 105.0, "confidence": 0.75, "source": "previous_high"}
            ],
            "valuation_summary": {
                "current_price": 102.5,
                "fair_estimate": 105.0,
                "discount_to_fair": 0.024,
                "is_undervalued": True
            },
            "recommendations": [
                {
                    "type": "LEAPS_CALL",
                    "strike": 100.0,
                    "expiry": "2024-12-20",
                    "entry_price": 3.0,
                    "confidence": 0.7
                }
            ]
        }

        document = vector_store._prepare_analysis_document(analysis_data)

        assert "Symbol: QQQ" in document
        assert "Date: 2024-01-10" in document
        assert "Analysis: Strong bullish momentum" in document
        assert "Support levels: $95.0, $98.5" in document
        assert "Resistance levels: $105.0" in document
        assert "Valuation: current $102.5, fair $105.0" in document
        assert "Recommendations: LEAPS_CALL at $100.0" in document

    def test_prepare_note_document(self, vector_store):
        """Test market note document preparation."""
        note_data = {
            "symbol": "SPY",
            "category": "technical",
            "content": "Breaking above 200-day moving average",
            "tags": ["breakout", "momentum", "technical"]
        }

        document = vector_store._prepare_note_document(note_data)

        assert "Symbol: SPY" in document
        assert "Category: technical" in document
        assert "Note: Breaking above 200-day moving average" in document
        assert "Tags: breakout, momentum, technical" in document

    def test_prepare_action_document(self, vector_store):
        """Test trading action document preparation."""
        action_data = {
            "symbol": "NVDA",
            "action_type": "BUY_CALL",
            "contract_symbol": "NVDA241220C500",
            "strike": 500.0,
            "option_type": "CALL",
            "notes": "Earnings play"
        }

        document = vector_store._prepare_action_document(action_data)

        assert "Symbol: NVDA" in document
        assert "Action: BUY_CALL" in document
        assert "Contract: NVDA241220C500" in document
        assert "Strike: $500.0" in document
        assert "Option type: CALL" in document
        assert "Notes: Earnings play" in document

    def test_add_and_search_analysis(self, vector_store):
        """Test adding and searching analysis."""
        # Add analysis
        analysis_data = {
            "symbol": "QQQ",
            "trade_date": "2024-01-10",
            "action_report": "Strong bullish momentum with clear support at $95",
            "support_levels": [{"price": 95.0, "confidence": 0.8, "source": "volume_profile"}],
            "resistance_levels": [{"price": 105.0, "confidence": 0.75, "source": "previous_high"}]
        }

        success = vector_store.add_analysis(1, analysis_data)
        assert success is True

        # Search with related query
        results = vector_store.search_analysis("bullish momentum support", limit=1)
        assert len(results) == 1
        assert results[0]["id"] == 1
        assert results[0]["metadata"]["symbol"] == "QQQ"
        assert "distance" in results[0]

        # Search with symbol filter
        results = vector_store.search_analysis("support", symbol="QQQ", limit=1)
        assert len(results) == 1
        assert results[0]["metadata"]["symbol"] == "QQQ"

        # Search with wrong symbol (should return empty)
        results = vector_store.search_analysis("support", symbol="SPY", limit=1)
        assert len(results) == 0

    def test_add_and_search_market_notes(self, vector_store):
        """Test adding and searching market notes."""
        # Add market note
        note_data = {
            "symbol": "SPY",
            "category": "technical",
            "content": "Breaking above 200-day moving average with high volume",
            "tags": ["breakout", "volume", "technical"]
        }

        success = vector_store.add_market_note(1, note_data)
        assert success is True

        # Search with related query
        results = vector_store.search_market_notes("moving average breakout", limit=1)
        assert len(results) == 1
        assert results[0]["id"] == 1
        assert results[0]["metadata"]["symbol"] == "SPY"
        assert results[0]["metadata"]["category"] == "technical"

        # Search with category filter
        results = vector_store.search_market_notes("volume", category="technical", limit=1)
        assert len(results) == 1

        # Search with symbol and category filter
        results = vector_store.search_market_notes("breakout", symbol="SPY", category="technical", limit=1)
        assert len(results) == 1

    def test_add_and_search_trading_actions(self, vector_store):
        """Test adding and searching trading actions."""
        # Add trading action
        action_data = {
            "symbol": "NVDA",
            "action_type": "BUY_CALL",
            "contract_symbol": "NVDA241220C500",
            "strike": 500.0,
            "option_type": "CALL",
            "notes": "Earnings play with strong guidance"
        }

        success = vector_store.add_trading_action(1, action_data)
        assert success is True

        # Search with related query
        results = vector_store.search_trading_actions("earnings call option", limit=1)
        assert len(results) == 1
        assert results[0]["id"] == 1
        assert results[0]["metadata"]["symbol"] == "NVDA"
        assert results[0]["metadata"]["action_type"] == "BUY_CALL"

        # Search with action type filter
        results = vector_store.search_trading_actions("call", action_type="BUY_CALL", limit=1)
        assert len(results) == 1

    def test_delete_operations(self, vector_store):
        """Test delete operations."""
        # Add test data
        analysis_data = {"symbol": "TEST", "action_report": "Test analysis"}
        note_data = {"symbol": "TEST", "content": "Test note"}
        action_data = {"symbol": "TEST", "action_type": "TEST"}

        vector_store.add_analysis(1, analysis_data)
        vector_store.add_market_note(1, note_data)
        vector_store.add_trading_action(1, action_data)

        # Delete and verify
        assert vector_store.delete_analysis(1) is True
        assert vector_store.delete_market_note(1) is True
        assert vector_store.delete_trading_action(1) is True

        # Verify deletions
        results = vector_store.search_analysis("test", limit=1)
        assert len(results) == 0

        results = vector_store.search_market_notes("test", limit=1)
        assert len(results) == 0

        results = vector_store.search_trading_actions("test", limit=1)
        assert len(results) == 0

    def test_get_stats(self, vector_store):
        """Test getting vector store statistics."""
        # Add some test data
        analysis_data = {"symbol": "TEST", "action_report": "Test"}
        note_data = {"symbol": "TEST", "content": "Test note"}
        action_data = {"symbol": "TEST", "action_type": "TEST"}

        vector_store.add_analysis(1, analysis_data)
        vector_store.add_market_note(1, note_data)
        vector_store.add_trading_action(1, action_data)

        # Get stats
        stats = vector_store.get_stats()

        assert "analysis_results" in stats
        assert "market_notes" in stats
        assert "trading_actions" in stats
        assert "total" in stats
        assert "embedding_dimension" in stats
        assert "storage_path" in stats

        assert stats["analysis_results"] >= 1
        assert stats["market_notes"] >= 1
        assert stats["trading_actions"] >= 1
        assert stats["total"] >= 3
        assert stats["embedding_dimension"] == 384

    def test_empty_query_embedding(self, vector_store):
        """Test embedding generation for empty text."""
        embedding = vector_store._generate_embedding("")
        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert all(x == 0.0 for x in embedding)

    def test_partial_data_preparation(self, vector_store):
        """Test document preparation with partial data."""
        # Test with minimal analysis data
        minimal_analysis = {"symbol": "QQQ"}
        document = vector_store._prepare_analysis_document(minimal_analysis)
        assert "Symbol: QQQ" in document
        assert "Date: " in document  # Empty date

        # Test with minimal note data
        minimal_note = {"content": "Test note"}
        document = vector_store._prepare_note_document(minimal_note)
        assert "Note: Test note" in document

        # Test with minimal action data
        minimal_action = {"action_type": "BUY"}
        document = vector_store._prepare_action_document(minimal_action)
        assert "Action: BUY" in document

"""Tests for Aegis-Memory semantic search and vector store integration."""

import os
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.aegis_memory.agent import AegisMemoryAgent
from src.models import (
    AgentState,
    OHLCV,
    OptionChain,
    OptionContract,
    OptionType,
    SupportResistanceLevel,
    ValuationRange,
)


@pytest.fixture
def temp_db_path():
    """Create a temporary database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def sample_state():
    """Create a minimal AgentState for testing."""
    ohlcv = OHLCV(
        symbol="QQQ",
        timestamp=datetime(2024, 1, 10),
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.5,
        volume=1000000
    )
    state = AgentState(
        symbol="QQQ",
        trade_date=date(2024, 1, 10),
        ohlcv_data=[ohlcv],
        action_report="Bullish momentum with support at $99",
        support_levels=[
            SupportResistanceLevel(price=99.0, level_type="support", confidence=0.8, source="volume_profile")
        ],
        resistance_levels=[
            SupportResistanceLevel(price=105.0, level_type="resistance", confidence=0.7, source="gex")
        ],
    )
    return state


@pytest.fixture
def agent_with_vector_store(temp_db_path):
    """Create agent with vector store support."""
    with patch("src.agents.aegis_memory.agent.get_config") as mock_get_config:
        mock_config = MagicMock()
        mock_config.memory.sqlite_path = temp_db_path
        mock_get_config.return_value = mock_config

        agent = AegisMemoryAgent()
        return agent


@pytest.fixture
def initialized_agent(agent_with_vector_store):
    """Create and initialize agent with isolated vector store."""
    import tempfile

    agent = agent_with_vector_store

    # Ensure SQLite schema exists
    agent._storage.ensure_schema()

    # Create isolated vector store for each test to avoid ID conflicts
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            from src.agents.aegis_memory.vector_store import VectorStore
            agent._vector_store = VectorStore(Path(temp_dir))
        except ImportError:
            pytest.skip("Vector store dependencies not installed")

        yield agent


class TestSemanticSearchAnalysis:
    """Test semantic search for analysis results."""

    @pytest.mark.asyncio
    async def test_search_analysis_semantic(self, initialized_agent, sample_state):
        """Test semantic search for analysis results."""
        agent = initialized_agent

        # Record analysis
        await agent.run(sample_state)

        # Search with related query
        results = await agent.search_analysis_semantic("bullish momentum support", symbol="QQQ", limit=1)

        assert len(results) == 1
        assert results[0]["symbol"] == "QQQ"
        assert "vector_metadata" in results[0]
        assert "similarity_score" in results[0]["vector_metadata"]
        assert "document" in results[0]["vector_metadata"]

    @pytest.mark.asyncio
    async def test_search_analysis_semantic_no_symbol_filter(self, initialized_agent, sample_state):
        """Test semantic search without symbol filter."""
        agent = initialized_agent
        await agent.run(sample_state)

        results = await agent.search_analysis_semantic("support", limit=5)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_analysis_semantic_no_results(self, initialized_agent):
        """Test semantic search with no matching results."""
        agent = initialized_agent

        results = await agent.search_analysis_semantic("nonexistent query xyz123", limit=1)
        assert len(results) == 0


class TestSemanticSearchMarketNotes:
    """Test semantic search for market notes."""

    @pytest.mark.asyncio
    async def test_search_market_notes_semantic(self, initialized_agent):
        """Test semantic search for market notes."""
        agent = initialized_agent

        # Add market note
        note = {
            "symbol": "SPY",
            "note_date": date(2024, 1, 10),
            "category": "technical",
            "content": "Breaking above 200-day moving average with strong volume",
            "tags": ["breakout", "volume"]
        }
        await agent.add_market_note(note)

        # Search
        results = await agent.search_market_notes_semantic("moving average breakout", symbol="SPY", limit=1)

        assert len(results) == 1
        assert results[0]["symbol"] == "SPY"
        assert "vector_metadata" in results[0]

    @pytest.mark.asyncio
    async def test_search_market_notes_semantic_with_category(self, initialized_agent):
        """Test semantic search with category filter."""
        agent = initialized_agent

        note = {
            "symbol": "QQQ",
            "note_date": date(2024, 1, 10),
            "category": "earnings",
            "content": "Strong earnings beat with raised guidance",
            "tags": ["earnings", "bullish"]
        }
        await agent.add_market_note(note)

        results = await agent.search_market_notes_semantic("earnings guidance", symbol="QQQ", category="earnings", limit=1)
        assert len(results) == 1


class TestSemanticSearchTradingActions:
    """Test semantic search for trading actions."""

    @pytest.mark.asyncio
    async def test_search_trading_actions_semantic(self, initialized_agent):
        """Test semantic search for trading actions."""
        agent = initialized_agent

        # Add trading action
        action = {
            "symbol": "NVDA",
            "action_date": date(2024, 1, 15),
            "action_type": "BUY_CALL",
            "contract_symbol": "NVDA241220C500",
            "strike": 500.0,
            "option_type": "CALL",
            "quantity": 10,
            "entry_price": 5.0,
            "notes": "Earnings play with strong guidance expectation"
        }
        await agent.add_trading_action(action)

        # Search
        results = await agent.search_trading_actions_semantic("earnings call option", symbol="NVDA", limit=1)

        assert len(results) == 1
        assert results[0]["symbol"] == "NVDA"
        assert "vector_metadata" in results[0]

    @pytest.mark.asyncio
    async def test_search_trading_actions_semantic_with_action_type(self, initialized_agent):
        """Test semantic search with action type filter."""
        agent = initialized_agent

        action = {
            "symbol": "QQQ",
            "action_date": date(2024, 1, 10),
            "action_type": "BUY_CALL",
            "strike": 100.0,
            "quantity": 5,
            "notes": "Long-term LEAPS position for portfolio growth"
        }
        await agent.add_trading_action(action)

        results = await agent.search_trading_actions_semantic("LEAPS long term", symbol="QQQ", action_type="BUY_CALL", limit=1)
        assert len(results) == 1


class TestVectorStoreStats:
    """Test vector store statistics."""

    @pytest.mark.asyncio
    async def test_get_vector_store_stats(self, initialized_agent, sample_state):
        """Test getting vector store statistics."""
        agent = initialized_agent

        # Add some data
        await agent.run(sample_state)

        note = {"symbol": "SPY", "note_date": date(2024, 1, 10), "category": "technical", "content": "Test note"}
        await agent.add_market_note(note)

        action = {"symbol": "QQQ", "action_date": date(2024, 1, 10), "action_type": "BUY"}
        await agent.add_trading_action(action)

        # Get stats
        stats = await agent.get_vector_store_stats()

        assert "error" not in stats
        assert stats["analysis_results"] >= 1
        assert stats["market_notes"] >= 1
        assert stats["trading_actions"] >= 1
        assert stats["total"] >= 3
        assert stats["embedding_dimension"] == 384
        assert "storage_path" in stats


class TestVectorStoreFallback:
    """Test behavior when vector store is unavailable."""

    @pytest.fixture
    def agent_without_vector_store(self, temp_db_path):
        """Create agent with vector store disabled."""
        with patch("src.agents.aegis_memory.agent.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.memory.sqlite_path = temp_db_path
            mock_get_config.return_value = mock_config

            agent = AegisMemoryAgent()
            # Simulate initialization failure by not calling initialize
            # or by setting vector_store to None after init
            agent._vector_store = None
            return agent

    @pytest.mark.asyncio
    async def test_search_analysis_semantic_fallback(self, agent_without_vector_store):
        """Test semantic search fallback when vector store unavailable."""
        results = await agent_without_vector_store.search_analysis_semantic("test query", limit=1)
        assert results == []

    @pytest.mark.asyncio
    async def test_search_market_notes_semantic_fallback(self, agent_without_vector_store):
        """Test market notes semantic search fallback."""
        results = await agent_without_vector_store.search_market_notes_semantic("test query", limit=1)
        assert results == []

    @pytest.mark.asyncio
    async def test_search_trading_actions_semantic_fallback(self, agent_without_vector_store):
        """Test trading actions semantic search fallback."""
        results = await agent_without_vector_store.search_trading_actions_semantic("test query", limit=1)
        assert results == []

    @pytest.mark.asyncio
    async def test_get_vector_store_stats_fallback(self, agent_without_vector_store):
        """Test stats fallback when vector store unavailable."""
        stats = await agent_without_vector_store.get_vector_store_stats()
        assert "error" in stats

    @pytest.mark.asyncio
    async def test_run_without_vector_store(self, agent_without_vector_store, sample_state):
        """Test that run() works without vector store."""
        # Initialize storage schema only
        agent_without_vector_store._storage.ensure_schema()

        result = await agent_without_vector_store.run(sample_state)

        assert result.symbol == "QQQ"
        assert any("Aegis-Memory" in step for step in result.agent_sequence)

        # Verify data was still recorded to SQLite
        import sqlite3
        with sqlite3.connect(agent_without_vector_store._db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM analysis_results")
            count = cursor.fetchone()[0]
        assert count == 1


class TestVectorStoreIntegration:
    """Test vector store integration with SQLite operations."""

    @pytest.mark.asyncio
    async def test_run_populates_vector_store(self, initialized_agent, sample_state):
        """Test that run() adds analysis to both SQLite and vector store."""
        agent = initialized_agent

        await agent.run(sample_state)

        # Verify SQLite has the record
        import sqlite3
        with sqlite3.connect(agent._db_path) as conn:
            cursor = conn.execute("SELECT id FROM analysis_results WHERE symbol = ?", ("QQQ",))
            row = cursor.fetchone()
        assert row is not None

        # Verify vector store has the record by searching
        results = await agent.search_analysis_semantic("bullish", symbol="QQQ", limit=1)
        assert len(results) == 1
        assert results[0]["id"] == row[0]

    @pytest.mark.asyncio
    async def test_add_trading_action_populates_vector_store(self, initialized_agent):
        """Test that add_trading_action adds to both SQLite and vector store."""
        agent = initialized_agent

        action = {
            "symbol": "TSLA",
            "action_date": date(2024, 1, 10),
            "action_type": "BUY_PUT",
            "strike": 200.0,
            "quantity": 5,
            "notes": "Hedge position for downside protection"
        }
        await agent.add_trading_action(action)

        # Verify vector store has the record
        results = await agent.search_trading_actions_semantic("hedge downside", symbol="TSLA", limit=1)
        assert len(results) == 1
        assert results[0]["symbol"] == "TSLA"

    @pytest.mark.asyncio
    async def test_add_market_note_populates_vector_store(self, initialized_agent):
        """Test that add_market_note adds to both SQLite and vector store."""
        agent = initialized_agent

        note = {
            "symbol": "AAPL",
            "note_date": date(2024, 1, 10),
            "category": "fundamental",
            "content": "iPhone sales exceeding expectations in China market",
            "tags": ["earnings", "china"]
        }
        await agent.add_market_note(note)

        # Verify vector store has the record
        results = await agent.search_market_notes_semantic("China iPhone sales", symbol="AAPL", limit=1)
        assert len(results) == 1
        assert results[0]["symbol"] == "AAPL"

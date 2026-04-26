"""Tests for Aegis-Memory Agent."""

import os
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.aegis_memory import queries
from src.agents.aegis_memory.agent import AegisMemoryAgent
from src.agents.aegis_memory.storage import AnalysisStorage
from src.models import (
    OHLCV,
    AgentState,
    OptionChain,
    OptionContract,
    OptionType,
    RecommendedOption,
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
def sample_agent_state():
    """Create a sample AgentState for testing."""
    ohlcv_data = [
        OHLCV(
            symbol="QQQ",
            timestamp=datetime(2024, 1, 1),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000000
        ),
        OHLCV(
            symbol="QQQ",
            timestamp=datetime(2024, 1, 2),
            open=100.5,
            high=102.0,
            low=100.0,
            close=101.5,
            volume=1200000
        )
    ]

    option_contract = OptionContract(
        symbol="QQQ240621C00150000",
        underlying="QQQ",
        contract_symbol="QQQ240621C00150000",
        strike=150.0,
        expiry=date(2024, 6, 21),
        option_type=OptionType.CALL,
        last_price=5.0,
        bid=4.8,
        ask=5.2,
        volume=100,
        open_interest=500
    )

    options_chain = OptionChain(
        symbol="QQQ",
        timestamp=datetime(2024, 1, 2),
        spot_price=101.5,
        calls=[option_contract],
        puts=[],
        expiry_dates=[date(2024, 6, 21)]
    )

    support_level = SupportResistanceLevel(
        price=100.0,
        level_type="support",
        confidence=0.85,
        source="volume_profile"
    )

    valuation = ValuationRange(
        symbol="QQQ",
        timestamp=datetime(2024, 1, 2),
        current_price=101.5,
        low_estimate=95.0,
        fair_estimate=110.0,
        high_estimate=120.0,
        method="pe_band",
        confidence=0.8
    )

    recommendation = RecommendedOption(
        contract=option_contract,
        recommendation_type="leaps_call",
        entry_price=5.0,
        target_price=10.0,
        stop_loss=3.0,
        risk_reward_ratio=2.5,
        confidence=0.75,
        reasoning="Strong support at 100, undervalued"
    )

    state = AgentState(
        symbol="QQQ",
        trade_date=date(2024, 1, 2),
        ohlcv_data=ohlcv_data,
        options_chain=options_chain,
        support_levels=[support_level],
        resistance_levels=[],
        valuation_range=valuation,
        recommended_options=[recommendation],
        action_report="Test action report"
    )
    state.add_agent_step("Data-Harvester")
    state.add_agent_step("Quant-Brain")

    return state


class TestAnalysisStorage:
    """Tests for AnalysisStorage class."""

    def test_ensure_schema_creates_tables(self, temp_db_path):
        """Test that ensure_schema creates all required tables."""
        storage = AnalysisStorage(Path(temp_db_path))
        storage.ensure_schema()

        # Verify tables exist by querying sqlite_master
        import sqlite3
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = {row[0] for row in cursor.fetchall()}

        assert "analysis_results" in tables
        assert "trading_actions" in tables
        assert "market_notes" in tables

    def test_record_analysis(self, temp_db_path, sample_agent_state):
        """Test recording analysis results."""
        storage = AnalysisStorage(Path(temp_db_path))
        storage.ensure_schema()
        storage.record_analysis(sample_agent_state)

        import sqlite3
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.execute("SELECT * FROM analysis_results")
            row = cursor.fetchone()

        assert row is not None
        assert row[1] == "QQQ"  # symbol
        assert row[2] == "2024-01-02"  # trade_date
        assert "Data-Harvester" in row[3]  # agent_sequence
        assert "Test action report" in row[10]  # action_report

    def test_record_analysis_no_data(self, temp_db_path):
        """Test recording analysis with minimal state."""
        state = AgentState(symbol="SPY", trade_date=date.today())
        storage = AnalysisStorage(Path(temp_db_path))
        storage.ensure_schema()
        storage.record_analysis(state)

        import sqlite3
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.execute("SELECT * FROM analysis_results")
            row = cursor.fetchone()

        assert row is not None
        assert row[1] == "SPY"


class TestQueries:
    """Tests for query operations."""

    @pytest.fixture(autouse=True)
    def setup_schema(self, temp_db_path):
        """Ensure schema exists before each test."""
        storage = AnalysisStorage(Path(temp_db_path))
        storage.ensure_schema()
        self.db_path = temp_db_path

    @pytest.mark.asyncio
    async def test_recall_recent_analysis_empty(self, temp_db_path):
        """Test recall with no data."""
        results = await queries.recall_recent_analysis(temp_db_path, "QQQ")
        assert results == []

    @pytest.mark.asyncio
    async def test_recall_recent_analysis_with_data(self, temp_db_path, sample_agent_state):
        """Test recall after recording analysis."""
        storage = AnalysisStorage(Path(temp_db_path))
        storage.record_analysis(sample_agent_state)

        results = await queries.recall_recent_analysis(temp_db_path, "QQQ")

        assert len(results) == 1
        assert results[0]["symbol"] == "QQQ"
        assert results[0]["ohlcv_summary"]["latest_close"] == 101.5
        assert results[0]["ohlcv_summary"]["data_points"] == 2
        assert "agent_sequence" in results[0]

    @pytest.mark.asyncio
    async def test_recall_recent_analysis_limit(self, temp_db_path, sample_agent_state):
        """Test recall limit."""
        storage = AnalysisStorage(Path(temp_db_path))
        storage.record_analysis(sample_agent_state)
        storage.record_analysis(sample_agent_state)
        storage.record_analysis(sample_agent_state)

        results = await queries.recall_recent_analysis(temp_db_path, "QQQ", limit=2)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_add_and_recall_trading_action(self, temp_db_path):
        """Test adding and recalling trading actions."""
        action = {
            "symbol": "QQQ",
            "action_date": date(2024, 1, 15),
            "action_type": "buy_call",
            "contract_symbol": "QQQ240621C00150000",
            "strike": 150.0,
            "expiry": date(2024, 6, 21),
            "option_type": "call",
            "quantity": 10,
            "entry_price": 5.0,
            "notes": "Test trade"
        }

        result = await queries.add_trading_action(temp_db_path, action)
        assert result is True

        results = await queries.recall_trading_actions(temp_db_path, "QQQ")
        assert len(results) == 1
        assert results[0]["symbol"] == "QQQ"
        assert results[0]["action_type"] == "buy_call"
        assert results[0]["quantity"] == 10

    @pytest.mark.asyncio
    async def test_add_and_recall_market_note(self, temp_db_path):
        """Test adding and recalling market notes."""
        note = {
            "symbol": "QQQ",
            "note_date": date(2024, 1, 10),
            "category": "earnings",
            "content": "Strong earnings beat, guidance raised",
            "tags": ["earnings", "bullish"]
        }

        result = await queries.add_market_note(temp_db_path, note)
        assert result is True

        results = await queries.recall_market_notes(temp_db_path, "QQQ")
        assert len(results) == 1
        assert results[0]["symbol"] == "QQQ"
        assert results[0]["category"] == "earnings"
        assert results[0]["tags"] == ["earnings", "bullish"]

    @pytest.mark.asyncio
    async def test_recall_market_notes_filter_by_category(self, temp_db_path):
        """Test filtering market notes by category."""
        note1 = {"symbol": "QQQ", "note_date": date.today(), "category": "earnings", "content": "Earnings note"}
        note2 = {"symbol": "QQQ", "note_date": date.today(), "category": "technical", "content": "Technical note"}

        await queries.add_market_note(temp_db_path, note1)
        await queries.add_market_note(temp_db_path, note2)

        results = await queries.recall_market_notes(temp_db_path, "QQQ", category="earnings")
        assert len(results) == 1
        assert results[0]["category"] == "earnings"

    @pytest.mark.asyncio
    async def test_recall_all_trading_actions(self, temp_db_path):
        """Test recalling all trading actions without symbol filter."""
        action1 = {"symbol": "QQQ", "action_date": date.today(), "action_type": "buy"}
        action2 = {"symbol": "SPY", "action_date": date.today(), "action_type": "sell"}

        await queries.add_trading_action(temp_db_path, action1)
        await queries.add_trading_action(temp_db_path, action2)

        results = await queries.recall_trading_actions(temp_db_path, limit=10)
        assert len(results) == 2


class TestAegisMemoryAgent:
    """Tests for AegisMemoryAgent integration."""

    @pytest.fixture
    def agent(self, temp_db_path):
        """Create agent with temp database."""
        with patch('src.agents.aegis_memory.agent.get_config') as mock_get_config:
            mock_config = MagicMock()
            mock_config.memory.sqlite_path = temp_db_path
            mock_get_config.return_value = mock_config
            agent = AegisMemoryAgent()
            return agent

    @pytest.mark.asyncio
    async def test_initialize(self, agent):
        """Test agent initialization creates schema."""
        await agent.initialize()

        import sqlite3
        with sqlite3.connect(agent._db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = {row[0] for row in cursor.fetchall()}

        assert "analysis_results" in tables

    @pytest.mark.asyncio
    async def test_initialize_degrades_when_vector_store_init_fails(self, agent):
        """Test initialization degrades gracefully when vector store setup fails."""
        with patch('src.agents.aegis_memory.vector_store.VectorStore.__init__', side_effect=RuntimeError("chromadb unavailable")):
            await agent.initialize()

        assert agent._vector_store is None
        assert await agent.get_vector_store_stats() == {"error": "Vector store not available"}

    @pytest.mark.asyncio
    async def test_run_records_analysis(self, agent, sample_agent_state):
        """Test run() records analysis to database."""
        await agent.initialize()
        result = await agent.run(sample_agent_state)

        # Verify state is returned with agent step added
        assert result.symbol == "QQQ"
        assert any("Aegis-Memory" in step for step in result.agent_sequence)

        # Verify data was recorded
        records = await agent.recall_recent_analysis("QQQ")
        assert len(records) == 1
        assert records[0]["symbol"] == "QQQ"

    @pytest.mark.asyncio
    async def test_add_trading_action_via_agent(self, agent):
        """Test adding trading action through agent."""
        await agent.initialize()

        action = {
            "symbol": "QQQ",
            "action_date": date(2024, 1, 15),
            "action_type": "buy_call",
            "strike": 150.0,
            "quantity": 5
        }

        result = await agent.add_trading_action(action)
        assert result is True

        records = await agent.recall_trading_actions("QQQ")
        assert len(records) == 1
        assert records[0]["action_type"] == "buy_call"

    @pytest.mark.asyncio
    async def test_add_market_note_via_agent(self, agent):
        """Test adding market note through agent."""
        await agent.initialize()

        note = {
            "symbol": "QQQ",
            "note_date": date(2024, 1, 10),
            "category": "technical",
            "content": "Broke resistance at 102"
        }

        result = await agent.add_market_note(note)
        assert result is True

        records = await agent.recall_market_notes("QQQ")
        assert len(records) == 1
        assert records[0]["content"] == "Broke resistance at 102"

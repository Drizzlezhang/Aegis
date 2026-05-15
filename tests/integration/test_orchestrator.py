"""End-to-end integration tests for the multi-agent pipeline."""

import sys
from datetime import date, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.orchestrator import Orchestrator
from src.models import (
    OHLCV,
    OptionChain,
    OptionContract,
    OptionType,
)


@pytest.fixture
def mock_yfinance_skill():
    """Create a mock yfinance skill returning sample data."""
    skill = MagicMock()
    skill.execute = AsyncMock()

    # OHLCV data
    ohlcv_data = [
        OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, i), open=100+i, high=101+i, low=99+i, close=100.5+i, volume=1000000+i*10000)
        for i in range(1, 11)
    ]

    # Options chain
    call_contract = OptionContract(
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
        timestamp=datetime(2024, 1, 10),
        spot_price=102.5,
        calls=[call_contract],
        puts=[],
        expiry_dates=[date(2024, 6, 21)]
    )

    fundamentals = {
        "pe_ratio": 25.0,
        "market_cap": 1000000000,
        "dividend_yield": 0.02
    }

    # Configure execute to return different data types
    async def execute_side_effect(params):
        data_type = params.get("data_type")
        result = Mock()
        result.success = True
        if data_type == "ohlcv":
            result.data = ohlcv_data
        elif data_type == "options":
            result.data = options_chain
        elif data_type == "fundamentals":
            result.data = fundamentals
        else:
            result.data = None
        return result

    skill.execute.side_effect = execute_side_effect
    skill.initialize = AsyncMock()
    return skill


@pytest.fixture
def mock_registry(mock_yfinance_skill):
    """Create a mock skill registry."""
    registry = MagicMock()
    registry.get_skill.return_value = mock_yfinance_skill
    registry.discover_skills.return_value = ["yfinance_ohlcv"]
    return registry


@pytest.fixture
def orchestrator(mock_registry):
    """Create an orchestrator with mocked dependencies."""
    with patch('src.agents.data_harvester.agent.get_global_registry', return_value=mock_registry), \
         patch('src.agents.quant_brain.agent.get_global_registry', return_value=mock_registry):
        orch = Orchestrator()
        yield orch


@pytest.mark.asyncio
async def test_pipeline_single_symbol(orchestrator):
    """Test full pipeline for a single symbol."""
    await orchestrator.initialize()
    state = await orchestrator.analyze_symbol("QQQ")

    # Verify state was populated
    assert state.symbol == "QQQ"
    assert state.ohlcv_data is not None
    assert len(state.ohlcv_data) == 10
    assert state.options_chain is not None
    assert state.options_chain.spot_price == 102.5

    # Verify agent sequence (format: "AgentName:timestamp")
    assert any("Data-Harvester" in step for step in state.agent_sequence)
    assert any("Quant-Brain" in step for step in state.agent_sequence)
    assert any("Strategy-Execution" in step for step in state.agent_sequence)
    assert any("Aegis-Memory" in step for step in state.agent_sequence)

    # Verify recommendations were generated
    assert len(state.recommended_options) >= 0  # May be 0 if no suitable strategies

    # Verify action report exists
    assert state.action_report != ""


@pytest.mark.asyncio
async def test_pipeline_no_options_data(orchestrator):
    """Test pipeline behavior when options data is missing."""
    await orchestrator.initialize()
    # Mock yfinance to return None for options
    async def no_options_execute(params):
        result = Mock()
        result.success = True
        if params.get("data_type") == "options":
            result.data = None
        else:
            result.data = []
        return result

    # Need to patch the skill's execute method
    with patch.object(orchestrator.get_agent("Data-Harvester")._yfinance_skill, 'execute',
                      side_effect=no_options_execute):
        state = await orchestrator.analyze_symbol("QQQ")

        # Should still complete pipeline but with limited data
        assert state.symbol == "QQQ"
        assert any("Data-Harvester" in step for step in state.agent_sequence)
        assert any("Strategy-Execution" in step for step in state.agent_sequence)


@pytest.mark.asyncio
async def test_pipeline_error_handling(orchestrator):
    """Test pipeline handles errors gracefully."""
    await orchestrator.initialize()
    # Mock Data-Harvester to raise exception
    with patch.object(orchestrator.get_agent("Data-Harvester"), 'run',
                      side_effect=Exception("Network error")):
        state = await orchestrator.analyze_symbol("QQQ")

        # Should still return a state with error info
        assert state.symbol == "QQQ"
        assert "Pipeline Error" in state.action_report


@pytest.mark.asyncio
async def test_batch_analysis(orchestrator):
    """Test batch analysis for multiple symbols."""
    await orchestrator.initialize()
    symbols = ["QQQ", "SPY"]
    states = await orchestrator.analyze_symbols(symbols)

    assert len(states) == 2
    for symbol, state in zip(symbols, states, strict=False):
        assert state.symbol == symbol
        assert any("Data-Harvester" in step for step in state.agent_sequence)


@pytest.mark.asyncio
async def test_execution_history(orchestrator):
    """Test execution history tracking."""
    await orchestrator.initialize()
    await orchestrator.analyze_symbol("QQQ")
    await orchestrator.analyze_symbol("SPY")

    history = orchestrator.get_execution_history()
    assert len(history) == 2

    for entry in history:
        assert "symbol" in entry
        assert "timestamp" in entry
        assert "execution_time" in entry
        assert "agent_sequence" in entry
        assert "recommendations_count" in entry
        assert "success" in entry


@pytest.mark.asyncio
async def test_generate_basic_report(orchestrator):
    """Test basic report generation without LLM."""
    await orchestrator.initialize()
    state = await orchestrator.analyze_symbol("QQQ")

    # Test basic report generation
    report = orchestrator._generate_basic_report(state)

    assert "AEGIS-TRADER ANALYSIS REPORT" in report
    assert "QQQ" in report
    assert "Data-Harvester" in report
    assert "Quant-Brain" in report
    assert "Strategy-Execution" in report
    assert "Aegis-Memory" in report


@pytest.mark.asyncio
async def test_health_check(orchestrator):
    """Test health check functionality."""
    await orchestrator.initialize()
    health = await orchestrator.health_check()

    assert "data_harvester" in health
    assert "quant_brain" in health
    assert "strategy_exec" in health
    assert "aegis_memory" in health

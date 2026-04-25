"""Tests for Data-Harvester Agent."""

import sys
from datetime import date, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.data_harvester.agent import DataHarvesterAgent
from src.models import AgentState


@pytest.fixture
def mock_yfinance_skill():
    """Create a mock yfinance skill."""
    skill = MagicMock()
    skill.execute = AsyncMock()
    skill.initialize = AsyncMock()
    return skill


@pytest.fixture
def data_harvester_agent():
    """Create DataHarvesterAgent instance for testing."""
    with patch('src.agents.data_harvester.agent.get_global_registry') as mock_get_registry:
        mock_registry = MagicMock()
        mock_get_registry.return_value = mock_registry
        agent = DataHarvesterAgent()
        yield agent


@pytest.fixture
def data_harvester_agent_with_skill(data_harvester_agent, mock_yfinance_skill):
    """Create DataHarvesterAgent with mock skill directly attached."""
    # Directly set the skill to bypass initialize() requirement
    data_harvester_agent._yfinance_skill = mock_yfinance_skill
    data_harvester_agent._skills["yfinance_ohlcv"] = mock_yfinance_skill
    data_harvester_agent._data_source_priority = ["yfinance_ohlcv"]
    yield data_harvester_agent


@pytest.mark.asyncio
async def test_agent_initialization(data_harvester_agent, mock_yfinance_skill):
    """Test DataHarvesterAgent initialization loads skill from registry."""
    # Patch registry to return mock skill
    data_harvester_agent._skill_registry.get_skill.return_value = mock_yfinance_skill

    await data_harvester_agent.initialize()

    assert data_harvester_agent.name == "Data-Harvester"
    assert data_harvester_agent._yfinance_skill is mock_yfinance_skill
    mock_yfinance_skill.initialize.assert_called_once()


@pytest.mark.asyncio
async def test_run_success(data_harvester_agent_with_skill, mock_yfinance_skill):
    """Test successful agent execution."""
    symbol = "QQQ"

    mock_ohlcv_data = [
        Mock(timestamp=datetime(2024, 1, 1), close=100.0, volume=1000000),
        Mock(timestamp=datetime(2024, 1, 2), close=101.0, volume=1200000)
    ]

    mock_options_chain = Mock(
        calls=[Mock(strike=150.0), Mock(strike=155.0)],
        puts=[Mock(strike=145.0), Mock(strike=140.0)],
        spot_price=102.5,
        expiry_dates=[date(2024, 6, 21), date(2024, 12, 20)],
        get_nearest_expiry=Mock(return_value=date(2024, 6, 21))
    )

    mock_fundamentals = {
        "pe_ratio": 25.0,
        "market_cap": 1000000000,
        "dividend_yield": 0.02
    }

    # Use regular Mock objects with success/data attributes as return values
    mock_market_indices = [
        {"symbol": "^VIX", "name": "VIX", "price": 20.0, "change": 0.5, "change_percent": 2.5},
    ]
    mock_yfinance_skill.execute.side_effect = [
        Mock(success=True, data=mock_ohlcv_data),
        Mock(success=True, data=mock_options_chain),
        Mock(success=True, data=mock_fundamentals),
        Mock(success=True, data=mock_market_indices),
    ]

    initial_state = AgentState(symbol=symbol, trade_date=date.today())
    result_state = await data_harvester_agent_with_skill.run(initial_state)

    assert result_state.symbol == symbol
    assert result_state.ohlcv_data == mock_ohlcv_data
    assert result_state.options_chain == mock_options_chain
    assert mock_yfinance_skill.execute.call_count == 4
    assert len(result_state.agent_sequence) == 1
    assert "Data-Harvester" in result_state.agent_sequence[0]


@pytest.mark.asyncio
async def test_run_missing_skill(data_harvester_agent):
    """Test agent execution when skill is missing."""
    symbol = "QQQ"
    data_harvester_agent._yfinance_skill = None

    initial_state = AgentState(symbol=symbol, trade_date=date.today())
    result_state = await data_harvester_agent.run(initial_state)

    assert result_state.ohlcv_data is None
    assert result_state.options_chain is None


@pytest.mark.asyncio
async def test_get_ohlcv_data_success(data_harvester_agent_with_skill, mock_yfinance_skill):
    """Test successful OHLCV data retrieval."""
    symbol = "QQQ"
    mock_data = [Mock(timestamp=datetime(2024, 1, 1), close=100.0, volume=1000000)]

    mock_yfinance_skill.execute.return_value = Mock(success=True, data=mock_data)

    result = await data_harvester_agent_with_skill._get_ohlcv_data(symbol)

    assert result == mock_data
    mock_yfinance_skill.execute.assert_called_once()
    call_args = mock_yfinance_skill.execute.call_args[0][0]
    assert call_args["symbol"] == symbol
    assert call_args["data_type"] == "ohlcv"
    assert call_args["interval"] == "1d"


@pytest.mark.asyncio
async def test_get_ohlcv_data_failure(data_harvester_agent_with_skill, mock_yfinance_skill):
    """Test failed OHLCV data retrieval."""
    mock_yfinance_skill.execute.return_value = Mock(success=False, error="Network error")

    result = await data_harvester_agent_with_skill._get_ohlcv_data("QQQ")
    assert result is None


@pytest.mark.asyncio
async def test_get_options_chain_success(data_harvester_agent_with_skill, mock_yfinance_skill):
    """Test successful options chain retrieval."""
    symbol = "QQQ"
    mock_chain = Mock(
        calls=[Mock(strike=150.0), Mock(strike=155.0)],
        puts=[Mock(strike=145.0), Mock(strike=140.0)],
        spot_price=102.5,
        expiry_dates=[date(2024, 6, 21), date(2024, 12, 20)]
    )

    mock_yfinance_skill.execute.return_value = Mock(success=True, data=mock_chain)

    result = await data_harvester_agent_with_skill._get_options_chain(symbol)

    assert result == mock_chain
    mock_yfinance_skill.execute.assert_called_once_with({
        "symbol": symbol,
        "data_type": "options"
    })


@pytest.mark.asyncio
async def test_get_fundamentals_success(data_harvester_agent_with_skill, mock_yfinance_skill):
    """Test successful fundamental data retrieval."""
    symbol = "QQQ"
    mock_fundamentals = {
        "pe_ratio": 25.0,
        "market_cap": 1000000000,
        "dividend_yield": 0.02
    }

    mock_yfinance_skill.execute.return_value = Mock(success=True, data=mock_fundamentals)

    result = await data_harvester_agent_with_skill._get_fundamentals(symbol)

    assert result == mock_fundamentals
    mock_yfinance_skill.execute.assert_called_once_with({
        "symbol": symbol,
        "data_type": "fundamentals"
    })


@pytest.mark.asyncio
async def test_get_all_data_parallel(data_harvester_agent_with_skill, mock_yfinance_skill):
    """Test parallel data retrieval."""
    symbol = "QQQ"

    mock_ohlcv = [Mock(timestamp=datetime(2024, 1, 1), close=100.0, volume=1000000)]
    mock_options = Mock(calls=[Mock(strike=150.0)], puts=[Mock(strike=145.0)], spot_price=102.5)
    mock_fundamentals = {"pe_ratio": 25.0}
    mock_market_indices = [{"symbol": "^VIX", "name": "VIX", "price": 20.0, "change": 0.5, "change_percent": 2.5}]

    mock_yfinance_skill.execute.side_effect = [
        Mock(success=True, data=mock_ohlcv),
        Mock(success=True, data=mock_options),
        Mock(success=True, data=mock_fundamentals),
        Mock(success=True, data=mock_market_indices),
    ]

    result = await data_harvester_agent_with_skill._get_all_data(symbol)

    assert result["ohlcv"] == mock_ohlcv
    assert result["options"] == mock_options
    assert result["fundamentals"] == mock_fundamentals
    assert result["market_indices"] == mock_market_indices
    assert mock_yfinance_skill.execute.call_count == 4


@pytest.mark.asyncio
async def test_health_check_success(data_harvester_agent_with_skill, mock_yfinance_skill):
    """Test successful health check."""
    mock_yfinance_skill.execute.return_value = Mock(success=True)

    result = await data_harvester_agent_with_skill.health_check()

    assert result is True


@pytest.mark.asyncio
async def test_health_check_failure(data_harvester_agent_with_skill, mock_yfinance_skill):
    """Test failed health check."""
    mock_yfinance_skill.execute.return_value = Mock(success=False)

    result = await data_harvester_agent_with_skill.health_check()

    assert result is False


def test_analysis_report_generation(data_harvester_agent_with_skill):
    """Test analysis report generation."""
    symbol = "QQQ"

    mock_data = {
        "ohlcv": [
            Mock(timestamp=datetime(2024, 1, 1), close=100.0, volume=1000000),
            Mock(timestamp=datetime(2024, 1, 2), close=101.0, volume=1200000)
        ],
        "options": Mock(
            calls=[Mock(strike=150.0), Mock(strike=155.0)],
            puts=[Mock(strike=145.0), Mock(strike=140.0)],
            spot_price=102.5,
            expiry_dates=[date(2024, 6, 21), date(2024, 12, 20)],
            get_nearest_expiry=Mock(return_value=date(2024, 6, 21))
        ),
        "fundamentals": {
            "pe_ratio": 25.0,
            "market_cap": 1000000000,
            "dividend_yield": 0.02
        }
    }

    report = data_harvester_agent_with_skill._create_analysis_report(symbol, mock_data)

    assert f"Data-Harvester Report for {symbol}" in report
    assert "OHLCV" in report
    assert "Options" in report
    assert "P/E Ratio" in report
    assert "Close=" in report
    assert "Spot Price:" in report


def test_analysis_report_no_data(data_harvester_agent):
    """Test report generation with no data."""
    symbol = "QQQ"
    mock_data = {"ohlcv": None, "options": None, "fundamentals": None}

    report = data_harvester_agent._create_analysis_report(symbol, mock_data)

    assert "Failed to retrieve" in report or "No data available" in report

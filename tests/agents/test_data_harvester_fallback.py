"""Tests for DataHarvesterAgent fallback logic."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from datetime import date

from src.agents.data_harvester.agent import DataHarvesterAgent
from src.models import AgentState
from src.skills.base import SkillResult


class FakeSkill:
    """Fake skill for testing."""

    def __init__(self, name: str, fail: bool = False):
        self.name = name
        self.fail = fail
        self.execute = AsyncMock()
        self.initialize = AsyncMock()

    def setup_success(self, data):
        self.execute.return_value = SkillResult.success_result(data)

    def setup_failure(self, error="error"):
        self.execute.return_value = SkillResult.error_result(error)


class TestDataHarvesterFallback:
    """Tests for automatic data source fallback."""

    @pytest.fixture
    def agent(self):
        with patch("src.agents.data_harvester.agent.get_config") as mock_config, \
             patch("src.agents.data_harvester.agent.get_global_registry") as mock_registry:

            cfg = MagicMock()
            cfg.data_source.yfinance_enabled = True
            cfg.data_source.alpha_vantage_enabled = True
            cfg.data_source.cache_ttl_seconds = 300
            mock_config.return_value = cfg

            registry = MagicMock()
            yf_skill = FakeSkill("yfinance_ohlcv")
            av_skill = FakeSkill("alpha_vantage_ohlcv")
            registry.get_skill.side_effect = lambda name: {
                "yfinance_ohlcv": yf_skill,
                "alpha_vantage_ohlcv": av_skill,
            }.get(name)
            mock_registry.return_value = registry

            a = DataHarvesterAgent()
            return a, yf_skill, av_skill

    @pytest.mark.asyncio
    async def test_yfinance_priority(self, agent):
        a, yf, av = agent
        await a.initialize()

        yf.setup_success([{"close": 100}])
        av.setup_success([{"close": 99}])

        result = await a._get_ohlcv_data("QQQ")
        assert result == [{"close": 100}]
        yf.execute.assert_awaited_once()
        av.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_fallback_to_alpha_vantage(self, agent):
        a, yf, av = agent
        await a.initialize()

        yf.setup_failure("timeout")
        av.setup_success([{"close": 99}])

        result = await a._get_ohlcv_data("QQQ")
        assert result == [{"close": 99}]
        yf.execute.assert_awaited_once()
        av.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_all_sources_fail(self, agent):
        a, yf, av = agent
        await a.initialize()

        yf.setup_failure("timeout")
        av.setup_failure("rate limit")

        result = await a._get_ohlcv_data("QQQ")
        assert result is None

    @pytest.mark.asyncio
    async def test_fundamentals_fallback(self, agent):
        a, yf, av = agent
        await a.initialize()

        yf.setup_failure("no data")
        av.setup_success({"pe_ratio": 26.4})

        result = await a._get_fundamentals("QQQ")
        assert result == {"pe_ratio": 26.4}

    @pytest.mark.asyncio
    async def test_options_only_yfinance(self, agent):
        a, yf, av = agent
        await a.initialize()

        yf.setup_success({"calls": [], "puts": []})

        result = await a._get_options_chain("QQQ")
        assert result == {"calls": [], "puts": []}
        av.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_run_updates_state(self, agent):
        a, yf, av = agent
        await a.initialize()

        yf.setup_success([{"close": 100}])

        state = AgentState(symbol="QQQ", trade_date=date.today())
        result = await a.run(state)

        assert result.symbol == "QQQ"
        assert len(result.agent_sequence) == 1
        assert "Data-Harvester" in result.agent_sequence[0]

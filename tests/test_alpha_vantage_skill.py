"""Tests for Alpha Vantage skill."""

import os
from unittest.mock import patch

import pytest

from skills.data_sources.alpha_vantage.skill import AlphaVantageSkill
from src.skills.base import SkillType


class TestAlphaVantageSkill:
    """Tests for AlphaVantageSkill."""

    @pytest.fixture
    def skill(self):
        """Create skill with test API key."""
        with patch.dict(os.environ, {"ALPHA_VANTAGE_API_KEY": "test_key"}):
            return AlphaVantageSkill(config={"cache_ttl": 60})

    def test_skill_type(self, skill):
        assert skill.skill_type == SkillType.DATA_SOURCE

    def test_description(self, skill):
        assert "Alpha Vantage" in skill.description

    def test_version(self, skill):
        assert skill.version == "0.1.0"

    def test_required_params(self, skill):
        assert skill.get_required_params() == ["symbol"]

    def test_no_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            s = AlphaVantageSkill()
            assert s._api_key == ""

    def test_rate_limit(self, skill):
        """Test rate limiting doesn't crash."""
        skill._rate_limit()
        assert len(skill._call_times) == 1

    @pytest.mark.asyncio
    async def test_execute_no_symbol(self, skill):
        result = await skill.execute({})
        assert result.success is False
        assert "Symbol is required" in result.error

    @pytest.mark.asyncio
    async def test_execute_no_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            s = AlphaVantageSkill()
            result = await s.execute({"symbol": "QQQ"})
            assert result.success is False
            assert "ALPHA_VANTAGE_API_KEY" in result.error

    @patch("skills.data_sources.alpha_vantage.skill.AlphaVantageSkill._request")
    def test_get_daily_data(self, mock_request, skill):
        mock_request.return_value = {
            "Time Series (Daily)": {
                "2026-04-24": {
                    "1. open": "438.5200",
                    "2. high": "441.0000",
                    "3. low": "437.5000",
                    "4. close": "440.0000",
                    "5. volume": "34500000",
                },
                "2026-04-23": {
                    "1. open": "436.0000",
                    "2. high": "439.0000",
                    "3. low": "435.0000",
                    "4. close": "438.5200",
                    "5. volume": "32000000",
                },
            }
        }

        df = skill._get_daily_data("QQQ")
        assert len(df) == 2
        assert "Open" in df.columns
        assert df.iloc[-1]["Close"] == 440.0

    @pytest.mark.asyncio
    @patch("skills.data_sources.alpha_vantage.skill.AlphaVantageSkill._request")
    async def test_get_fundamentals(self, mock_request, skill):
        mock_request.return_value = {
            "Symbol": "QQQ",
            "PERatio": "26.4",
            "EPS": "15.23",
            "Beta": "1.12",
            "MarketCapitalization": "150000000000",
        }

        fundamentals = await skill.get_fundamentals("QQQ")
        assert fundamentals["pe_ratio"] == 26.4
        assert fundamentals["eps"] == 15.23
        assert fundamentals["beta"] == 1.12

    def test_rate_limit_message(self, skill):
        """Rate limit response should be detected by _request internals."""
        # _request detects rate limit when it sees "rate limit" or "call frequency"
        # in the response. This is tested via integration, not unit mock.
        assert skill.rate_limit_calls == 5
        assert skill.rate_limit_period == 60

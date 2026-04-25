"""Tests for Longbridge skill."""

import os
from unittest.mock import Mock, patch

import pytest

from skills.data_sources.longbridge.skill import LongbridgeSkill
from src.skills.base import SkillType


class TestLongbridgeSkill:
    """Tests for LongbridgeSkill."""

    @pytest.fixture
    def skill(self):
        """Create skill with test credentials."""
        with patch.dict(
            os.environ,
            {
                "LONGBRIDGE_APP_KEY": "test_key",
                "LONGBRIDGE_APP_SECRET": "test_secret",
                "LONGBRIDGE_ACCESS_TOKEN": "test_token",
            },
        ):
            return LongbridgeSkill(config={"cache_ttl": 60, "market": "HK"})

    def test_skill_type(self, skill):
        assert skill.skill_type == SkillType.DATA_SOURCE

    def test_description(self, skill):
        assert "Longbridge" in skill.description

    def test_version(self, skill):
        assert skill.version == "0.1.0"

    def test_required_params(self, skill):
        assert skill.get_required_params() == ["symbol"]

    def test_no_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            s = LongbridgeSkill()
            assert s._app_key == ""
            assert s._app_secret == ""
            assert s._access_token == ""

    def test_headers(self, skill):
        headers = skill._headers()
        assert headers["X-Api-Key"] == "test_key"
        assert headers["X-Api-Secret"] == "test_secret"
        assert headers["Authorization"] == "Bearer test_token"

    def test_normalize_symbol_with_suffix(self, skill):
        """Symbols with suffix should pass through."""
        assert skill._normalize_symbol("00700.HK") == "00700.HK"
        assert skill._normalize_symbol("AAPL.US") == "AAPL.US"

    def test_normalize_symbol_without_suffix(self, skill):
        """Symbols without suffix should get market appended."""
        assert skill._normalize_symbol("00700") == "00700.HK"
        skill.market = "US"
        assert skill._normalize_symbol("AAPL") == "AAPL.US"

    @patch("skills.data_sources.longbridge.skill.requests.get")
    def test_request_success(self, mock_get, skill):
        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: {"code": 0, "data": {"candlesticks": []}},
            raise_for_status=Mock(),
        )

        result = skill._request("/v1/quote/candlesticks", {"symbol": "00700.HK"})
        assert result == {"candlesticks": []}

    @patch("skills.data_sources.longbridge.skill.requests.get")
    def test_request_api_error(self, mock_get, skill):
        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: {"code": 400, "message": "Invalid symbol"},
            raise_for_status=Mock(),
        )

        with pytest.raises(RuntimeError, match="Invalid symbol"):
            skill._request("/v1/quote/candlesticks", {"symbol": "INVALID"})

    @patch("skills.data_sources.longbridge.skill.requests.get")
    def test_request_retry_then_success(self, mock_get, skill):
        """Test retry logic: first request fails, second succeeds."""
        fail_response = Mock(
            status_code=200,
            json=lambda: {"code": 500, "message": "Server error"},
            raise_for_status=Mock(),
        )
        success_response = Mock(
            status_code=200,
            json=lambda: {"code": 0, "data": {"result": "ok"}},
            raise_for_status=Mock(),
        )
        mock_get.side_effect = [fail_response, success_response]

        result = skill._request("/test", {})
        assert result == {"result": "ok"}
        assert mock_get.call_count == 2

    @patch("skills.data_sources.longbridge.skill.LongbridgeSkill._request")
    def test_get_candlesticks(self, mock_request, skill):
        mock_request.return_value = {
            "candlesticks": [
                {
                    "timestamp": 1713974400,
                    "open": "400.0",
                    "high": "410.0",
                    "low": "395.0",
                    "close": "405.0",
                    "volume": "1000000",
                },
                {
                    "timestamp": 1714060800,
                    "open": "405.0",
                    "high": "415.0",
                    "low": "400.0",
                    "close": "412.0",
                    "volume": "1200000",
                },
            ]
        }

        candles = skill._get_candlesticks("00700", 2, "1d")
        assert len(candles) == 2
        assert candles[0]["open"] == "400.0"

    @patch("skills.data_sources.longbridge.skill.LongbridgeSkill._request")
    def test_candles_to_ohlcv(self, mock_request, skill):
        mock_request.return_value = {
            "candlesticks": [
                {
                    "timestamp": 1713974400,
                    "open": "400.0",
                    "high": "410.0",
                    "low": "395.0",
                    "close": "405.0",
                    "volume": "1000000",
                },
            ]
        }

        candles = skill._get_candlesticks("00700", 1, "1d")
        ohlcv = skill._candles_to_ohlcv(candles, "00700")
        assert len(ohlcv) == 1
        assert ohlcv[0].close == 405.0
        assert ohlcv[0].volume == 1000000

    @patch("skills.data_sources.longbridge.skill.LongbridgeSkill._request")
    def test_get_quote(self, mock_request, skill):
        mock_request.return_value = {
            "last_done": 405.0,
            "open": 400.0,
            "high": 410.0,
            "low": 395.0,
            "volume": 1000000,
            "turnover": 405000000,
            "timestamp": 1714156800,
        }

        import asyncio

        quote = asyncio.run(skill.get_quote("00700"))
        assert quote["symbol"] == "00700"
        assert quote["last_price"] == 405.0
        assert quote["volume"] == 1000000

    @pytest.mark.asyncio
    async def test_execute_no_symbol(self, skill):
        result = await skill.execute({})
        assert result.success is False
        assert "Symbol is required" in result.error

    @pytest.mark.asyncio
    async def test_execute_no_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            s = LongbridgeSkill()
            result = await s.execute({"symbol": "00700"})
            assert result.success is False
            assert "LONGBRIDGE_APP_KEY" in result.error

    @pytest.mark.asyncio
    @patch("skills.data_sources.longbridge.skill.LongbridgeSkill._request")
    async def test_execute_ohlcv(self, mock_request, skill):
        mock_request.return_value = {
            "candlesticks": [
                {
                    "timestamp": 1713974400,
                    "open": "400.0",
                    "high": "410.0",
                    "low": "395.0",
                    "close": "405.0",
                    "volume": "1000000",
                },
            ]
        }

        result = await skill.execute({"symbol": "00700", "data_type": "ohlcv"})
        assert result.success is True
        assert result.data is not None
        assert result.metadata["source"] == "longbridge"

    @pytest.mark.asyncio
    @patch("skills.data_sources.longbridge.skill.LongbridgeSkill._request")
    async def test_execute_quote(self, mock_request, skill):
        mock_request.return_value = {
            "last_done": 405.0,
            "open": 400.0,
            "high": 410.0,
            "low": 395.0,
            "volume": 1000000,
            "turnover": 405000000,
            "timestamp": 1714156800,
        }

        result = await skill.execute({"symbol": "00700", "data_type": "quote"})
        assert result.success is True
        assert result.data["last_price"] == 405.0

    @pytest.mark.asyncio
    async def test_execute_unknown_data_type(self, skill):
        result = await skill.execute({"symbol": "00700", "data_type": "unknown"})
        assert result.success is False
        assert "Unknown data_type" in result.error

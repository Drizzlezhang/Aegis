"""Tests for Tiger skill."""

import os
from unittest.mock import MagicMock, patch

import pytest

from skills.data_sources.tiger.skill import TigerSkill
from src.skills.base import SkillType


class TestTigerSkill:
    """Tests for TigerSkill."""

    @pytest.fixture
    def skill(self):
        """Create skill with test credentials."""
        with patch.dict(
            os.environ,
            {
                "TIGER_ACCOUNT_ID": "test_account",
                "TIGER_PRIVATE_KEY": "test_key",
            },
        ):
            return TigerSkill(config={"cache_ttl": 60, "market": "US"})

    def test_skill_type(self, skill):
        assert skill.skill_type == SkillType.DATA_SOURCE

    def test_description(self, skill):
        assert "Tiger" in skill.description

    def test_version(self, skill):
        assert skill.version == "0.1.0"

    def test_required_params(self, skill):
        assert skill.get_required_params() == ["symbol"]

    def test_no_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            s = TigerSkill()
            assert s._account_id == ""
            assert s._private_key == ""

    def test_normalize_symbol(self, skill):
        """Tiger symbols are passed as-is (market is separate)."""
        assert skill._normalize_symbol("AAPL") == "AAPL"
        assert skill._normalize_symbol("00700") == "00700"

    @patch("skills.data_sources.tiger.skill.TIGER_SDK_AVAILABLE", True)
    def test_get_tiger_market(self, skill):
        """Test market mapping when SDK is available."""
        with patch("skills.data_sources.tiger.skill.Market") as mock_market:
            mock_market.US = "US"
            mock_market.HK = "HK"
            mock_market.CN = "CN"

            assert skill._get_tiger_market() == "US"
            skill.market = "HK"
            assert skill._get_tiger_market() == "HK"

    @patch("skills.data_sources.tiger.skill.TIGER_SDK_AVAILABLE", True)
    def test_get_bar_period(self, skill):
        """Test bar period mapping."""
        with patch("skills.data_sources.tiger.skill.BarPeriod") as mock_period:
            mock_period.DAY = "day"
            mock_period.ONE_MINUTE = "1m"

            assert skill._get_bar_period("1d") == "day"

    def test_candles_to_ohlcv(self, skill):
        """Test candlestick conversion."""
        candlesticks = [
            {
                "timestamp": 1713974400,
                "open": 180.0,
                "high": 185.0,
                "low": 178.0,
                "close": 182.5,
                "volume": 5000000,
            },
            {
                "timestamp": 1714060800,
                "open": 182.5,
                "high": 188.0,
                "low": 180.0,
                "close": 187.0,
                "volume": 6000000,
            },
        ]

        ohlcv = skill._candles_to_ohlcv(candlesticks, "AAPL")
        assert len(ohlcv) == 2
        assert ohlcv[0].close == 182.5
        assert ohlcv[1].volume == 6000000

    @patch("skills.data_sources.tiger.skill.TIGER_SDK_AVAILABLE", True)
    @patch("skills.data_sources.tiger.skill.TigerOpenClient")
    @patch("skills.data_sources.tiger.skill.QuoteClient")
    @patch("skills.data_sources.tiger.skill.Market")
    @patch("skills.data_sources.tiger.skill.BarPeriod")
    def test_get_candlesticks_sdk(self, mock_bp, mock_mkt, mock_quote_class, mock_client_class, skill):
        """Test SDK-based candlestick retrieval."""
        import pandas as pd

        mock_quote = MagicMock()
        mock_quote_class.return_value = mock_quote

        mock_bars = pd.DataFrame([
            {
                "time": pd.Timestamp("2024-04-24"),
                "open": 180.0,
                "high": 185.0,
                "low": 178.0,
                "close": 182.5,
                "volume": 5000000,
            }
        ])
        mock_quote.get_bars.return_value = mock_bars

        skill._quote_client = mock_quote
        candles = skill._get_candlesticks_sdk("AAPL", 1, "1d")

        assert len(candles) == 1
        assert candles[0]["close"] == 182.5
        mock_quote.get_bars.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_no_symbol(self, skill):
        result = await skill.execute({})
        assert result.success is False
        assert "Symbol is required" in result.error

    @pytest.mark.asyncio
    async def test_execute_no_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            s = TigerSkill()
            result = await s.execute({"symbol": "AAPL"})
            assert result.success is False
            assert "TIGER_ACCOUNT_ID" in result.error

    @pytest.mark.asyncio
    async def test_execute_unknown_data_type(self, skill):
        result = await skill.execute({"symbol": "AAPL", "data_type": "unknown"})
        assert result.success is False
        assert "Unknown data_type" in result.error

    @patch("skills.data_sources.tiger.skill.TIGER_SDK_AVAILABLE", True)
    @patch("skills.data_sources.tiger.skill.TigerOpenClient")
    @patch("skills.data_sources.tiger.skill.QuoteClient")
    def test_initialize_with_sdk(self, mock_quote_class, mock_client_class, skill):
        """Test initialization with SDK available."""
        import asyncio

        mock_quote = MagicMock()
        mock_quote_class.return_value = mock_quote

        asyncio.run(skill.initialize())
        mock_client_class.assert_called_once()
        mock_quote_class.assert_called_once()

    def test_initialize_without_sdk(self, skill):
        """Test initialization falls back gracefully without SDK."""
        import asyncio

        with patch("skills.data_sources.tiger.skill.TIGER_SDK_AVAILABLE", False):
            asyncio.run(skill.initialize())
            assert skill._quote_client is None

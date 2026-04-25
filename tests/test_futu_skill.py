"""Tests for Futu skill."""

import os
from unittest.mock import MagicMock, Mock, patch

import pytest

from skills.data_sources.futu.skill import FutuSkill
from src.skills.base import SkillType


class TestFutuSkill:
    """Tests for FutuSkill."""

    @pytest.fixture
    def skill(self):
        """Create skill with test config."""
        with patch.dict(
            os.environ,
            {
                "FUTU_OPEND_ADDRESS": "127.0.0.1",
                "FUTU_OPEND_PORT": "11111",
            },
        ):
            return FutuSkill(config={"cache_ttl": 60, "market": "HK"})

    def test_skill_type(self, skill):
        assert skill.skill_type == SkillType.DATA_SOURCE

    def test_description(self, skill):
        assert "Futu" in skill.description

    def test_version(self, skill):
        assert skill.version == "0.1.0"

    def test_required_params(self, skill):
        assert skill.get_required_params() == ["symbol"]

    def test_no_credentials(self):
        s = FutuSkill()
        s._opend_address = ""
        assert s._opend_address == ""
        assert s._opend_port == 11111

    def test_normalize_symbol_with_suffix(self, skill):
        assert skill._normalize_symbol("00700.HK") == "00700.HK"
        assert skill._normalize_symbol("AAPL.US") == "AAPL.US"

    def test_normalize_symbol_without_suffix(self, skill):
        assert skill._normalize_symbol("00700") == "00700.HK"
        skill.market = "US"
        assert skill._normalize_symbol("AAPL") == "AAPL.US"

    @pytest.mark.asyncio
    async def test_execute_no_symbol(self, skill):
        result = await skill.execute({})
        assert result.success is False
        assert "Symbol is required" in result.error

    @pytest.mark.asyncio
    async def test_execute_no_credentials(self):
        s = FutuSkill()
        s._opend_address = ""
        result = await s.execute({"symbol": "00700"})
        assert result.success is False
        assert "Futu OpenD not configured" in result.error

    @pytest.mark.asyncio
    async def test_execute_unknown_data_type(self, skill):
        result = await skill.execute({"symbol": "00700", "data_type": "unknown"})
        assert result.success is False
        assert "Unknown data_type" in result.error

    @patch("skills.data_sources.futu.skill.FUTU_SDK_AVAILABLE", True)
    def test_get_kl_type(self, skill):
        """Test KLType mapping when SDK is available."""
        with patch("skills.data_sources.futu.skill.KLType") as mock_kl:
            mock_kl.K_1M = "1m"
            mock_kl.K_DAY = "day"
            mock_kl.K_WEEK = "week"

            result = skill._get_kl_type("1d")
            assert result == "day"

    def test_candles_to_ohlcv(self, skill):
        """Test candlestick conversion."""
        candlesticks = [
            {
                "timestamp": 1713974400,
                "open": 400.0,
                "high": 410.0,
                "low": 395.0,
                "close": 405.0,
                "volume": 1000000,
            },
            {
                "timestamp": 1714060800,
                "open": 405.0,
                "high": 415.0,
                "low": 400.0,
                "close": 412.0,
                "volume": 1200000,
            },
        ]

        ohlcv = skill._candles_to_ohlcv(candlesticks, "00700")
        assert len(ohlcv) == 2
        assert ohlcv[0].close == 405.0
        assert ohlcv[1].volume == 1200000

    @patch("skills.data_sources.futu.skill.FUTU_SDK_AVAILABLE", True)
    @patch("skills.data_sources.futu.skill.OpenQuoteContext")
    @patch("skills.data_sources.futu.skill.KLType")
    @patch("skills.data_sources.futu.skill.RET_OK", 0)
    def test_get_candlesticks_sdk(self, mock_kl, mock_ctx_class, skill):
        """Test SDK-based candlestick retrieval."""
        mock_ctx = MagicMock()
        mock_ctx_class.return_value = mock_ctx

        # Mock DataFrame result
        import pandas as pd
        mock_data = pd.DataFrame([
            {
                "time_key": pd.Timestamp("2024-04-24"),
                "open": 400.0,
                "high": 410.0,
                "low": 395.0,
                "close": 405.0,
                "volume": 1000000,
            }
        ])
        mock_ctx.request_history_kl.return_value = (0, mock_data, None)

        skill._quote_ctx = mock_ctx
        candles = skill._get_candlesticks_sdk("00700", 1, "1d")

        assert len(candles) == 1
        assert candles[0]["open"] == 400.0
        mock_ctx.request_history_kl.assert_called_once()

    @patch("skills.data_sources.futu.skill.FUTU_SDK_AVAILABLE", True)
    @patch("skills.data_sources.futu.skill.OpenQuoteContext")
    def test_initialize_with_sdk(self, mock_ctx_class, skill):
        """Test initialization with SDK available."""
        import asyncio

        asyncio.run(skill.initialize())
        mock_ctx_class.assert_called_once_with(host="127.0.0.1", port=11111)
        assert skill._quote_ctx is not None

    def test_initialize_without_sdk(self, skill):
        """Test initialization falls back gracefully without SDK."""
        import asyncio

        with patch("skills.data_sources.futu.skill.FUTU_SDK_AVAILABLE", False):
            asyncio.run(skill.initialize())
            assert skill._quote_ctx is None

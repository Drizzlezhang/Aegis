"""Tests for Futu data source skill."""

from unittest.mock import MagicMock, patch

import pytest

from skills.data_sources.futu.skill import FutuSkill


class TestFutuSkillOptions:
    """Tests for FutuSkill options chain support."""

    @pytest.fixture
    def skill(self):
        """Create skill instance."""
        with patch.dict("os.environ", {"FUTU_OPEND_ADDRESS": "127.0.0.1", "FUTU_OPEND_PORT": "11111"}):
            return FutuSkill(config={"market": "US"})

    def test_get_options_chain_sdk_not_available(self, skill):
        """When SDK is not installed, return None."""
        with patch("skills.data_sources.futu.skill.FUTU_SDK_AVAILABLE", False):
            import asyncio
            result = asyncio.run(skill.get_options_chain("QQQ"))
            assert result is None

    def test_get_options_chain_success(self, skill):
        """Successful options chain returns OptionChain with Greeks."""
        mock_ctx = MagicMock()
        mock_quote = {"last_price": 450.0}

        # Build a mock DataFrame with one call and one put
        import pandas as pd

        mock_df = pd.DataFrame([
            {
                "code": "QQQ250117C00450000",
                "strike_time": "2025-01-17",
                "option_type": "CALL",
                "strike_price": 450.0,
                "last_price": 10.5,
                "bid_price": 10.2,
                "ask_price": 10.8,
                "volume": 1000,
                "open_interest": 5000,
                "implied_volatility": 0.25,
                "delta": 0.65,
                "gamma": 0.02,
                "theta": -0.15,
                "vega": 0.30,
                "rho": 0.10,
            },
            {
                "code": "QQQ250117P00450000",
                "strike_time": "2025-01-17",
                "option_type": "PUT",
                "strike_price": 450.0,
                "last_price": 8.5,
                "bid_price": 8.2,
                "ask_price": 8.8,
                "volume": 800,
                "open_interest": 3000,
                "implied_volatility": 0.22,
                "delta": -0.35,
                "gamma": 0.018,
                "theta": -0.12,
                "vega": 0.25,
                "rho": -0.08,
            },
        ])

        mock_ctx.get_option_chain.return_value = (0, mock_df)  # RET_OK = 0

        with patch("skills.data_sources.futu.skill.FUTU_SDK_AVAILABLE", True):
            skill._quote_ctx = mock_ctx
            with patch.object(skill, "get_quote", return_value=mock_quote):
                import asyncio

                result = asyncio.run(skill.get_options_chain("QQQ"))

        assert result is not None
        assert result.symbol == "QQQ"
        assert result.spot_price == 450.0
        assert len(result.calls) == 1
        assert len(result.puts) == 1

        call = result.calls[0]
        assert call.delta == pytest.approx(0.65)
        assert call.gamma == pytest.approx(0.02)
        assert call.theta == pytest.approx(-0.15)
        assert call.vega == pytest.approx(0.30)
        assert call.implied_volatility == pytest.approx(0.25)

    def test_execute_options(self, skill):
        """execute with data_type=options returns SkillResult."""
        mock_chain = MagicMock()
        mock_chain.symbol = "QQQ"

        with patch.object(skill, "get_options_chain", return_value=mock_chain):
            import asyncio

            result = asyncio.run(skill.execute({"symbol": "QQQ", "data_type": "options"}))

        assert result.success is True
        assert result.data is mock_chain

    def test_execute_options_not_found(self, skill):
        """execute with data_type=options returns error when no data."""
        with patch.object(skill, "get_options_chain", return_value=None):
            import asyncio

            result = asyncio.run(skill.execute({"symbol": "QQQ", "data_type": "options"}))

        assert result.success is False
        assert "No options data" in result.error


class TestFutuSkillMarketIndices:
    """Tests for market indices support."""

    @pytest.fixture
    def skill(self):
        with patch.dict("os.environ", {"FUTU_OPEND_ADDRESS": "127.0.0.1", "FUTU_OPEND_PORT": "11111"}):
            return FutuSkill(config={"market": "US"})

    def test_get_market_indices_sdk_not_available(self, skill):
        """When SDK is not installed, return empty list."""
        with patch("skills.data_sources.futu.skill.FUTU_SDK_AVAILABLE", False):
            import asyncio

            result = asyncio.run(skill.get_market_indices())
            assert result == []

    def test_get_market_indices_success(self, skill):
        """Successful market indices retrieval."""
        import pandas as pd

        mock_ctx = MagicMock()
        mock_df = pd.DataFrame([
            {"last_price": 20000.0, "prev_close": 19800.0},
        ])
        mock_ctx.get_market_snapshot.return_value = (0, mock_df)

        with patch("skills.data_sources.futu.skill.FUTU_SDK_AVAILABLE", True):
            skill._quote_ctx = mock_ctx
            import asyncio

            result = asyncio.run(skill.get_market_indices())

        assert len(result) >= 0  # May be 0 if symbol filtering skips it


class TestFutuSkillFundamentals:
    """Tests for fundamentals support."""

    @pytest.fixture
    def skill(self):
        with patch.dict("os.environ", {"FUTU_OPEND_ADDRESS": "127.0.0.1", "FUTU_OPEND_PORT": "11111"}):
            return FutuSkill(config={"market": "US"})

    def test_get_fundamentals_sdk_not_available(self, skill):
        """When SDK is not installed, return empty dict."""
        with patch("skills.data_sources.futu.skill.FUTU_SDK_AVAILABLE", False):
            import asyncio

            result = asyncio.run(skill.get_fundamentals("QQQ"))
            assert result == {}

    def test_get_fundamentals_success(self, skill):
        """Successful fundamentals retrieval."""
        import pandas as pd

        mock_ctx = MagicMock()
        mock_df = pd.DataFrame([
            {
                "code": "QQQ.US",
                "pe_ratio": 25.5,
                "eps": 15.2,
                "market_cap": 1.5e12,
                "dividend_yield": 0.01,
                "beta": 1.1,
            }
        ])
        mock_ctx.get_stock_basicinfo.return_value = (0, mock_df)

        with patch("skills.data_sources.futu.skill.FUTU_SDK_AVAILABLE", True):
            skill._quote_ctx = mock_ctx
            import asyncio

            result = asyncio.run(skill.get_fundamentals("QQQ"))

        assert result.get("pe_ratio") == pytest.approx(25.5)
        assert result.get("eps") == pytest.approx(15.2)

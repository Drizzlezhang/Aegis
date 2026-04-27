"""Tests for symbol API endpoints."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_watchlist_cache() -> None:
    from src.api.routes import symbols

    symbols._watchlist_cache["expires_at"] = 0.0
    symbols._watchlist_cache["data"] = None


class TestGetSymbols:
    """Tests for GET /api/symbols."""

    def test_returns_latest_symbol_data_from_live_quote_source(self) -> None:
        mock_skill = MagicMock()
        mock_skill.get_ohlcv = AsyncMock(return_value=[])
        mock_skill.get_fundamentals = AsyncMock(
            return_value={
                "market_cap": 1500000000000,
                "average_volume": 42000000,
                "volume": 36000000,
            }
        )

        with patch("src.api.routes.symbols.YFinanceSkill", return_value=mock_skill):
            response = client.get("/api/symbols")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_symbol_payload_uses_quote_and_fundamentals_values(self) -> None:
        ohlcv_point = MagicMock(close=512.34, open=500.0, volume=12345678)
        mock_skill = MagicMock()
        mock_skill.get_ohlcv = AsyncMock(return_value=[ohlcv_point])
        mock_skill.get_fundamentals = AsyncMock(
            return_value={
                "market_cap": 987654321000,
                "average_volume": 23000000,
                "volume": 12345678,
            }
        )

        with patch("src.api.routes.symbols.YFinanceSkill", return_value=mock_skill):
            response = client.get("/api/symbols")

        assert response.status_code == 200
        first = response.json()[0]
        assert first["price"] == 512.34
        assert first["volume"] == 12345678

    def test_caches_symbols_response_for_15_seconds(self) -> None:
        mock_skill = MagicMock()
        mock_skill.get_ohlcv = AsyncMock(return_value=[])
        mock_skill.get_fundamentals = AsyncMock(return_value={})

        with patch("src.api.routes.symbols.YFinanceSkill", return_value=mock_skill):
            first = client.get("/api/symbols")
            second = client.get("/api/symbols")

        assert first.status_code == 200
        assert second.status_code == 200
        assert mock_skill.get_ohlcv.await_count == 11
        assert mock_skill.get_fundamentals.await_count == 11

    def test_limits_highest_concurrency_with_request_pool(self) -> None:
        from src.api.routes import symbols

        active = 0
        peak = 0

        async def fake_ohlcv(*_args, **_kwargs):
            return []

        async def fake_fundamentals(*_args, **_kwargs):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            active -= 1
            return {}

        mock_skill = MagicMock()
        mock_skill.get_ohlcv = AsyncMock(side_effect=fake_ohlcv)
        mock_skill.get_fundamentals = AsyncMock(side_effect=fake_fundamentals)

        with patch("src.api.routes.symbols.YFinanceSkill", return_value=mock_skill):
            response = client.get("/api/symbols")

        assert response.status_code == 200
        assert peak <= symbols._WATCHLIST_MAX_CONCURRENCY

    def test_required_fields(self) -> None:
        response = client.get("/api/symbols")
        data = response.json()
        required = {"symbol", "name", "price", "change", "changePercent", "volume", "trend", "analysisStatus"}
        for symbol in data:
            assert required.issubset(symbol.keys())


class TestGetSymbolDetail:
    """Tests for GET /api/symbols/{symbol}."""

    def test_existing_symbol(self) -> None:
        response = client.get("/api/symbols/QQQ")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "QQQ"
        assert "supports" in data
        assert "resistances" in data
        assert "volumeProfile" in data
        assert "gexWalls" in data
        assert "recommendations" in data
        assert isinstance(data["supports"], list)
        assert isinstance(data["resistances"], list)

    def test_detail_payload_uses_latest_price_volume_and_fundamentals(self) -> None:
        ohlcv_points = [
            MagicMock(symbol="QQQ", open=500.0, close=505.0, volume=10000000),
            MagicMock(symbol="QQQ", open=506.0, close=512.34, volume=12345678),
        ]
        mock_skill = MagicMock()
        mock_skill.get_ohlcv = AsyncMock(return_value=ohlcv_points)
        mock_skill.get_fundamentals = AsyncMock(
            return_value={
                "market_cap": 987654321000,
                "average_volume": 23000000,
                "volume": 12345678,
                "pe_ratio": 31.25,
            }
        )

        with patch("src.api.routes.symbols.YFinanceSkill", return_value=mock_skill):
            response = client.get("/api/symbols/QQQ")

        assert response.status_code == 200
        data = response.json()
        assert data["price"] == 512.34
        assert data["change"] == 7.34
        assert data["changePercent"] == 1.45
        assert data["volume"] == 12345678
        assert data["avgVolume"] == 23000000
        assert data["marketCap"] == "$987.65B"
        assert data["peRatio"] == 31.25

    def test_detail_payload_uses_algorithmic_analysis_levels(self) -> None:
        ohlcv_points = [
            MagicMock(symbol="QQQ", open=500.0, close=505.0, volume=10000000),
            MagicMock(symbol="QQQ", open=506.0, close=512.34, volume=12345678),
        ]
        mock_skill = MagicMock()
        mock_skill.get_ohlcv = AsyncMock(return_value=ohlcv_points)
        mock_skill.get_fundamentals = AsyncMock(
            return_value={
                "market_cap": 987654321000,
                "average_volume": 23000000,
                "volume": 12345678,
                "pe_ratio": 31.25,
            }
        )
        mock_volume_profile = SimpleNamespace(
            poc_price=510.0,
            vah_price=520.0,
            val_price=500.0,
            total_volume=22345678.0,
        )
        support_levels = [
            SimpleNamespace(price=498.0, confidence=0.8, source="volume_profile"),
            SimpleNamespace(price=492.0, confidence=0.6, source="technical"),
        ]
        resistance_levels = [
            SimpleNamespace(price=518.0, confidence=0.7, source="volume_profile"),
            SimpleNamespace(price=525.0, confidence=0.8, source="gex"),
        ]

        with (
            patch("src.api.routes.symbols.YFinanceSkill", return_value=mock_skill),
            patch("src.api.routes.symbols.VolumeProfileSkill", create=True) as volume_profile_skill_cls,
            patch(
                "src.api.routes.symbols.create_support_resistance_levels",
                return_value=(support_levels, resistance_levels),
                create=True,
            ),
        ):
            volume_profile_skill_cls.return_value.calculate_volume_profile.return_value = mock_volume_profile
            response = client.get("/api/symbols/QQQ")

        assert response.status_code == 200
        data = response.json()
        assert data["volumeProfile"] == {
            "poc": 510.0,
            "vah": 520.0,
            "val": 500.0,
            "volumeAtPoc": 22345678,
        }
        assert data["supports"] == [
            {
                "level": 498.0,
                "type": "support",
                "strength": "strong",
                "source": "Volume Profile",
            },
            {
                "level": 492.0,
                "type": "support",
                "strength": "moderate",
                "source": "Technical",
            },
        ]
        assert data["resistances"] == [
            {
                "level": 518.0,
                "type": "resistance",
                "strength": "moderate",
                "source": "Volume Profile",
            },
            {
                "level": 525.0,
                "type": "resistance",
                "strength": "strong",
                "source": "GEX Wall",
            },
        ]

    def test_detail_payload_uses_real_gex_walls(self) -> None:
        ohlcv_points = [
            MagicMock(symbol="QQQ", open=500.0, close=505.0, volume=10000000),
            MagicMock(symbol="QQQ", open=506.0, close=512.34, volume=12345678),
        ]
        mock_skill = MagicMock()
        mock_skill.get_ohlcv = AsyncMock(return_value=ohlcv_points)
        mock_skill.get_fundamentals = AsyncMock(
            return_value={
                "market_cap": 987654321000,
                "average_volume": 23000000,
                "volume": 12345678,
                "pe_ratio": 31.25,
            }
        )
        mock_skill.get_options_chain = AsyncMock(return_value=SimpleNamespace(symbol="QQQ"))
        mock_gex_walls = [
            SimpleNamespace(strike=500.0, net_gex=-1800000.0, wall_type="support"),
            SimpleNamespace(strike=520.0, net_gex=2400000.0, wall_type="resistance"),
        ]

        with (
            patch("src.api.routes.symbols.YFinanceSkill", return_value=mock_skill),
            patch("src.api.routes.symbols.GEXCalculatorSkill", create=True) as gex_skill_cls,
        ):
            gex_skill_cls.return_value.calculate_gex_walls.return_value = mock_gex_walls
            response = client.get("/api/symbols/QQQ")

        assert response.status_code == 200
        data = response.json()
        assert data["gexWalls"] == [
            {
                "strike": 500,
                "gamma": -1800000.0,
                "type": "put",
                "strength": "strong",
            },
            {
                "strike": 520,
                "gamma": 2400000.0,
                "type": "call",
                "strength": "strong",
            },
        ]

    def test_detail_payload_uses_dynamic_recommendations(self) -> None:
        ohlcv_points = [
            MagicMock(symbol="QQQ", open=500.0, close=505.0, volume=10000000),
            MagicMock(symbol="QQQ", open=506.0, close=512.34, volume=12345678),
        ]
        mock_skill = MagicMock()
        mock_skill.get_ohlcv = AsyncMock(return_value=ohlcv_points)
        mock_skill.get_fundamentals = AsyncMock(
            return_value={
                "market_cap": 987654321000,
                "average_volume": 23000000,
                "volume": 12345678,
                "pe_ratio": 31.25,
            }
        )
        mock_skill.get_options_chain = AsyncMock(return_value=SimpleNamespace(symbol="QQQ"))
        mock_volume_profile = SimpleNamespace(
            poc_price=510.0,
            vah_price=520.0,
            val_price=500.0,
            total_volume=22345678.0,
        )
        support_levels = [SimpleNamespace(price=500.0, confidence=0.8, source="volume_profile")]
        resistance_levels = [SimpleNamespace(price=520.0, confidence=0.8, source="gex")]
        mock_gex_walls = [SimpleNamespace(strike=520.0, net_gex=2400000.0, wall_type="resistance")]

        with (
            patch("src.api.routes.symbols.YFinanceSkill", return_value=mock_skill),
            patch("src.api.routes.symbols.VolumeProfileSkill", create=True) as volume_profile_skill_cls,
            patch(
                "src.api.routes.symbols.create_support_resistance_levels",
                return_value=(support_levels, resistance_levels),
                create=True,
            ),
            patch("src.api.routes.symbols.GEXCalculatorSkill", create=True) as gex_skill_cls,
        ):
            volume_profile_skill_cls.return_value.calculate_volume_profile.return_value = mock_volume_profile
            gex_skill_cls.return_value.calculate_gex_walls.return_value = mock_gex_walls
            response = client.get("/api/symbols/QQQ")

        assert response.status_code == 200
        recs = response.json()["recommendations"]
        assert recs == [
            {
                "id": "support-leaps",
                "type": "LEAPS",
                "description": "Buy QQQ LEAPS Call near $500 support with upside to $520 resistance",
                "riskLevel": "medium",
                "expectedReturn": "1.5% to resistance",
                "expiration": "Jan 2027",
                "strike": "$500",
            },
            {
                "id": "resistance-bull-spread",
                "type": "Bull Spread",
                "description": "Structure QQQ bull call spread from $500 support toward $520 resistance",
                "riskLevel": "low",
                "expectedReturn": "Defined-risk upside into resistance",
                "expiration": "Jul 2026",
                "strike": "$500 / $520",
            },
            {
                "id": "gex-covered-call",
                "type": "Covered Call",
                "description": "Sell QQQ covered call into GEX resistance at $520",
                "riskLevel": "low",
                "expectedReturn": "Income at key resistance",
                "expiration": "May 2026",
                "strike": "$520",
            },
        ]

    def test_symbol_case_insensitive(self) -> None:
        response = client.get("/api/symbols/qqq")
        assert response.status_code == 200
        assert response.json()["symbol"] == "QQQ"

    def test_not_found(self) -> None:
        response = client.get("/api/symbols/UNKNOWN")
        assert response.status_code == 404
        assert "UNKNOWN" in response.json()["detail"]

    def test_support_resistance_structure(self) -> None:
        response = client.get("/api/symbols/SPY")
        data = response.json()
        for level in data["supports"]:
            assert "level" in level
            assert "type" in level
            assert "strength" in level
            assert "source" in level

    def test_volume_profile_structure(self) -> None:
        response = client.get("/api/symbols/NVDA")
        data = response.json()
        vp = data["volumeProfile"]
        assert "poc" in vp
        assert "vah" in vp
        assert "val" in vp
        assert "volumeAtPoc" in vp

    def test_recommendations_structure(self) -> None:
        response = client.get("/api/symbols/MSFT")
        data = response.json()
        recs = data["recommendations"]
        assert len(recs) == 3
        for rec in recs:
            assert "id" in rec
            assert "type" in rec
            assert "description" in rec
            assert "riskLevel" in rec
            assert "expectedReturn" in rec


class TestGetSymbolAnalysis:
    """Tests for GET /api/symbols/{symbol}/analysis."""

    def test_existing_symbol(self) -> None:
        response = client.get("/api/symbols/QQQ/analysis")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "QQQ"
        assert "supports" in data
        assert "resistances" in data
        assert "volumeProfile" in data
        assert "gexWalls" in data
        assert "recommendations" in data

    def test_not_found(self) -> None:
        response = client.get("/api/symbols/UNKNOWN/analysis")
        assert response.status_code == 404

    def test_data_consistency_with_detail(self) -> None:
        """Analysis endpoint should return same data as detail endpoint."""
        detail = client.get("/api/symbols/SPY").json()
        analysis = client.get("/api/symbols/SPY/analysis").json()
        assert analysis["price"] == detail["price"]
        assert analysis["supports"] == detail["supports"]

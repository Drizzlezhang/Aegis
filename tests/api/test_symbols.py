"""Tests for symbol API endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


class TestGetSymbols:
    """Tests for GET /api/symbols."""

    def test_returns_list(self) -> None:
        response = client.get("/api/symbols")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 11

    def test_symbol_structure(self) -> None:
        response = client.get("/api/symbols")
        data = response.json()
        symbol = data[0]
        assert symbol["symbol"] == "QQQ"
        assert symbol["name"] == "Invesco QQQ Trust"
        assert isinstance(symbol["price"], float)
        assert isinstance(symbol["volume"], int)
        assert symbol["trend"] in ("up", "down", "neutral")
        assert symbol["analysisStatus"] in ("completed", "pending", "error")

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

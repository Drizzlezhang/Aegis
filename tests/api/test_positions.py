"""Tests for positions API endpoints."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


class FakePositionService:
    def __init__(
        self,
        summary: dict | None = None,
        chain: list[dict] | None = None,
        alerts: dict | None = None,
        chain_error: Exception | None = None,
    ) -> None:
        self._summary = summary or {
            "total_positions": 0,
            "active_count": 0,
            "closed_count": 0,
            "total_realized_pnl": 0.0,
            "total_unrealized_pnl": 0.0,
            "positions": [],
        }
        self._chain = chain or []
        self._alerts = alerts or {"alerts": [], "scanned_at": "2026-05-16T00:00:00Z"}
        self._chain_error = chain_error

    async def load(self) -> None:
        return None

    async def get_summary(self) -> dict:
        return self._summary

    async def get_chain(self, _position_id: str) -> list[dict]:
        _ = _position_id
        if self._chain_error is not None:
            raise self._chain_error
        return self._chain

    async def get_alerts(self) -> dict:
        return self._alerts


class TestGetPositions:
    """Tests for positions routes."""

    def test_summary_returns_empty_when_no_positions(self) -> None:
        fake_service = FakePositionService()
        with patch("src.api.routes.positions._load_service", AsyncMock(return_value=fake_service)):
            response = client.get("/api/positions/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total_positions"] == 0
        assert data["active_count"] == 0
        assert data["closed_count"] == 0
        assert data["total_realized_pnl"] == 0
        assert data["total_unrealized_pnl"] == 0
        assert data["positions"] == []

    def test_chain_returns_404_when_position_missing(self) -> None:
        fake_service = FakePositionService(chain_error=KeyError("Position not found"))
        with patch("src.api.routes.positions._load_service", AsyncMock(return_value=fake_service)):
            response = client.get("/api/positions/not-found/chain")

        assert response.status_code == 404
        assert response.json() == {"detail": "Position not found"}

    def test_alerts_returns_empty_list(self) -> None:
        fake_service = FakePositionService(alerts={"alerts": [], "scanned_at": "2026-05-16T00:00:00Z"})
        with patch("src.api.routes.positions._load_service", AsyncMock(return_value=fake_service)):
            response = client.get("/api/positions/alerts")

        assert response.status_code == 200
        data = response.json()
        assert data["alerts"] == []
        assert isinstance(data["scanned_at"], str)
        assert data["scanned_at"]

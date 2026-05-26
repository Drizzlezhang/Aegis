"""Tests for Position CRUD API endpoints."""

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

    async def open_position(self, _req) -> dict:
        return {
            "id": "pos-001",
            "symbol": "AAPL",
            "status": "active",
            "strike": 200.0,
            "expiry": "2026-06-26",
            "dte": 31,
            "entry_price": 5.50,
            "current_price": 5.50,
            "pnl": 0.0,
            "pnl_pct": 0.0,
            "quantity": 1,
        }

    async def close_position(self, position_id: str, _req) -> dict:
        if position_id == "not-found":
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Position not found")
        return {
            "id": position_id,
            "symbol": "AAPL",
            "status": "closed",
            "strike": 200.0,
            "expiry": "2026-06-26",
            "dte": 0,
            "entry_price": 5.50,
            "current_price": 7.00,
            "pnl": 150.0,
            "pnl_pct": 27.27,
            "quantity": 1,
        }

    async def roll_position(self, position_id: str, _req) -> dict:
        if position_id == "not-found":
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Position not found")
        return {
            "old_position": {
                "id": position_id,
                "symbol": "AAPL",
                "status": "rolled",
                "strike": 200.0,
                "expiry": "2026-06-26",
                "dte": 0,
                "entry_price": 5.50,
                "current_price": 5.50,
                "pnl": 0.0,
                "pnl_pct": 0.0,
                "quantity": 1,
            },
            "new_position": {
                "id": "pos-002",
                "symbol": "AAPL",
                "status": "active",
                "strike": 210.0,
                "expiry": "2026-07-26",
                "dte": 61,
                "entry_price": 4.00,
                "current_price": 4.00,
                "pnl": 0.0,
                "pnl_pct": 0.0,
                "quantity": 1,
            },
        }

    async def update_position(self, position_id: str, _req) -> dict:
        if position_id == "not-found":
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Position not found")
        return {
            "id": position_id,
            "symbol": "AAPL",
            "status": "active",
            "strike": 200.0,
            "expiry": "2026-06-26",
            "dte": 31,
            "entry_price": 5.50,
            "current_price": 6.00,
            "pnl": 50.0,
            "pnl_pct": 9.09,
            "quantity": 1,
        }


class TestOpenPosition:
    def test_open_position_creates_active(self) -> None:
        fake_service = FakePositionService()
        with patch("src.api.routes.positions._load_service", AsyncMock(return_value=fake_service)):
            response = client.post("/api/positions", json={
                "symbol": "AAPL",
                "contract_type": "call",
                "strike": 200.0,
                "expiry": "2026-06-26",
                "entry_price": 5.50,
                "quantity": 1,
            })

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "pos-001"
        assert data["symbol"] == "AAPL"
        assert data["status"] == "active"
        assert data["strike"] == 200.0


class TestClosePosition:
    def test_close_position_sets_closed(self) -> None:
        fake_service = FakePositionService()
        with patch("src.api.routes.positions._load_service", AsyncMock(return_value=fake_service)):
            response = client.post("/api/positions/pos-001/close", json={
                "close_price": 7.00,
                "reason": "target_hit",
            })

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "closed"
        assert data["pnl"] == 150.0

    def test_close_nonexistent_returns_404(self) -> None:
        fake_service = FakePositionService()
        with patch("src.api.routes.positions._load_service", AsyncMock(return_value=fake_service)):
            response = client.post("/api/positions/not-found/close", json={
                "close_price": 7.00,
                "reason": "manual",
            })

        assert response.status_code == 404
        assert response.json() == {"detail": "Position not found"}


class TestRollPosition:
    def test_roll_position_creates_new_linked(self) -> None:
        fake_service = FakePositionService()
        with patch("src.api.routes.positions._load_service", AsyncMock(return_value=fake_service)):
            response = client.post("/api/positions/pos-001/roll", json={
                "new_strike": 210.0,
                "new_expiry": "2026-07-26",
                "new_entry_price": 4.00,
            })

        assert response.status_code == 200
        data = response.json()
        assert data["old_position"]["status"] == "rolled"
        assert data["new_position"]["status"] == "active"
        assert data["new_position"]["strike"] == 210.0
        assert data["new_position"]["id"] == "pos-002"


class TestUpdatePosition:
    def test_update_position_price(self) -> None:
        fake_service = FakePositionService()
        with patch("src.api.routes.positions._load_service", AsyncMock(return_value=fake_service)):
            response = client.patch("/api/positions/pos-001", json={
                "current_price": 6.00,
            })

        assert response.status_code == 200
        data = response.json()
        assert data["current_price"] == 6.00
        assert data["pnl"] == 50.0

    def test_update_position_notes(self) -> None:
        fake_service = FakePositionService()
        with patch("src.api.routes.positions._load_service", AsyncMock(return_value=fake_service)):
            response = client.patch("/api/positions/pos-001", json={
                "notes": "Updated notes",
            })

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "pos-001"

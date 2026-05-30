"""Tests for paper trading API routes."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture(autouse=True)
def _reset_paper_singletons():
    """Reset paper broker/portfolio singletons between tests."""
    import src.api.routes.paper as p
    p._broker = None
    p._portfolio = None
    yield
    p._broker = None
    p._portfolio = None


@pytest.fixture
def client():
    return TestClient(app)


class TestPaperOrders:
    def test_get_orders_empty(self, client):
        r = client.get("/api/paper/orders")
        assert r.status_code == 200
        assert r.json() == {"orders": [], "total": 0}

    def test_get_orders_with_status_filter(self, client):
        r = client.get("/api/paper/orders?status=filled")
        assert r.status_code == 200
        assert r.json() == {"orders": [], "total": 0}

    def test_get_orders_invalid_status(self, client):
        r = client.get("/api/paper/orders?status=invalid")
        assert r.status_code == 422

    def test_place_market_buy_order(self, client):
        r = client.post("/api/paper/orders", json={"symbol": "AAPL", "side": "buy", "quantity": 10})
        assert r.status_code == 201
        data = r.json()
        assert data["success"] is True
        assert data["orderId"]
        assert "filled" in data["message"]

    def test_place_market_sell_order(self, client):
        r = client.post("/api/paper/orders", json={"symbol": "AAPL", "side": "sell", "quantity": 5})
        assert r.status_code == 201
        data = r.json()
        assert data["success"] is True

    def test_place_limit_order(self, client):
        r = client.post("/api/paper/orders", json={
            "symbol": "NVDA", "side": "buy", "quantity": 5,
            "orderType": "limit", "limitPrice": 50.0,
        })
        assert r.status_code == 201
        data = r.json()
        assert data["success"] is True
        assert "pending" in data["message"]

    def test_place_order_invalid_side(self, client):
        r = client.post("/api/paper/orders", json={"symbol": "AAPL", "side": "invalid", "quantity": 10})
        assert r.status_code == 422

    def test_place_order_zero_quantity(self, client):
        r = client.post("/api/paper/orders", json={"symbol": "AAPL", "side": "buy", "quantity": 0})
        assert r.status_code == 422

    def test_place_order_invalid_type(self, client):
        r = client.post("/api/paper/orders", json={
            "symbol": "AAPL", "side": "buy", "quantity": 10,
            "orderType": "invalid",
        })
        assert r.status_code == 422

    def test_orders_persist_across_requests(self, client):
        client.post("/api/paper/orders", json={"symbol": "AAPL", "side": "buy", "quantity": 10})
        r = client.get("/api/paper/orders")
        assert r.status_code == 200
        assert r.json()["total"] == 1

    def test_cancel_pending_order(self, client):
        r = client.post("/api/paper/orders", json={
            "symbol": "NVDA", "side": "buy", "quantity": 5,
            "orderType": "limit", "limitPrice": 50.0,
        })
        order_id = r.json()["orderId"]

        r = client.delete(f"/api/paper/orders/{order_id}")
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_cancel_nonexistent_order(self, client):
        r = client.delete("/api/paper/orders/nonexistent")
        assert r.status_code == 404

    def test_cancel_filled_order_fails(self, client):
        r = client.post("/api/paper/orders", json={"symbol": "AAPL", "side": "buy", "quantity": 10})
        order_id = r.json()["orderId"]

        r = client.delete(f"/api/paper/orders/{order_id}")
        assert r.status_code == 404


class TestPaperPositions:
    def test_get_positions_empty(self, client):
        r = client.get("/api/paper/positions")
        assert r.status_code == 200
        assert r.json() == {"positions": [], "total": 0}

    def test_positions_after_buy(self, client):
        client.post("/api/paper/orders", json={"symbol": "AAPL", "side": "buy", "quantity": 10})
        r = client.get("/api/paper/positions")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert data["positions"][0]["symbol"] == "AAPL"
        assert data["positions"][0]["quantity"] == 10

    def test_positions_after_buy_and_sell(self, client):
        client.post("/api/paper/orders", json={"symbol": "AAPL", "side": "buy", "quantity": 10})
        client.post("/api/paper/orders", json={"symbol": "AAPL", "side": "sell", "quantity": 3})
        r = client.get("/api/paper/positions")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert data["positions"][0]["quantity"] == 7


class TestPaperPortfolio:
    def test_get_portfolio_default(self, client):
        r = client.get("/api/paper/portfolio")
        assert r.status_code == 200
        data = r.json()
        assert data["cash"] == 100000.0
        assert data["equity"] == 100000.0
        assert data["positionCount"] == 0

    def test_portfolio_after_trades(self, client):
        client.post("/api/paper/orders", json={"symbol": "AAPL", "side": "buy", "quantity": 10})
        r = client.get("/api/paper/portfolio")
        assert r.status_code == 200
        data = r.json()
        assert data["positionCount"] == 1
        assert data["cash"] < 100000.0


class TestPaperReset:
    def test_reset_clears_state(self, client):
        client.post("/api/paper/orders", json={"symbol": "AAPL", "side": "buy", "quantity": 10})
        r = client.post("/api/paper/reset")
        assert r.status_code == 200
        assert r.json()["success"] is True

        r = client.get("/api/paper/orders")
        assert r.json()["total"] == 0

        r = client.get("/api/paper/positions")
        assert r.json()["total"] == 0

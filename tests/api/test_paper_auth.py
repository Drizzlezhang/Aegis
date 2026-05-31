"""Tests for Paper API authentication (P0-3 hotfix)."""

import pytest
from fastapi.testclient import TestClient

from src.agents.strategy_exec.brokers.paper import PaperBroker
from src.api.main import app
from src.config import get_config
from src.services.portfolio_service import PortfolioService


@pytest.fixture
def client() -> TestClient:
    # Ensure app.state has paper_broker and paper_portfolio for tests
    if not hasattr(app.state, "paper_broker"):
        app.state.paper_broker = PaperBroker()
    if not hasattr(app.state, "paper_portfolio"):
        app.state.paper_portfolio = PortfolioService(app.state.paper_broker)
    return TestClient(app)


class TestPaperEndpoint401WithoutToken:
    """Verify paper endpoints return 401 when token is configured but missing."""

    def test_paper_endpoint_401_without_token(self, client: TestClient, monkeypatch) -> None:
        """GET /api/paper/orders should return 401 when token is set but not provided."""
        monkeypatch.setattr(get_config(), "paper_token", "test-token")

        response = client.get("/api/paper/orders")
        assert response.status_code == 401

    def test_paper_post_401_without_token(self, client: TestClient, monkeypatch) -> None:
        """POST /api/paper/orders should return 401 when token is set but not provided."""
        monkeypatch.setattr(get_config(), "paper_token", "test-token")

        response = client.post("/api/paper/orders", json={
            "symbol": "AAPL",
            "side": "buy",
            "quantity": 10,
        })
        assert response.status_code == 401

    def test_paper_delete_401_without_token(self, client: TestClient, monkeypatch) -> None:
        """DELETE /api/paper/orders/{id} should return 401 when token is set but not provided."""
        monkeypatch.setattr(get_config(), "paper_token", "test-token")

        response = client.delete("/api/paper/orders/test-id")
        assert response.status_code == 401

    def test_paper_reset_401_without_token(self, client: TestClient, monkeypatch) -> None:
        """POST /api/paper/reset should return 401 when token is set but not provided."""
        monkeypatch.setattr(get_config(), "paper_token", "test-token")

        response = client.post("/api/paper/reset")
        assert response.status_code == 401


class TestPaperEndpoint200WithValidToken:
    """Verify paper endpoints work with valid token."""

    def test_paper_endpoint_200_with_valid_token(self, client: TestClient, monkeypatch) -> None:
        """GET /api/paper/orders should return 200 with valid Bearer token."""
        monkeypatch.setattr(get_config(), "paper_token", "test-token")

        response = client.get(
            "/api/paper/orders",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200

    def test_paper_endpoint_200_with_x_aegis_token(self, client: TestClient, monkeypatch) -> None:
        """GET /api/paper/orders should return 200 with X-Aegis-Token header."""
        monkeypatch.setattr(get_config(), "paper_token", "test-token")

        response = client.get(
            "/api/paper/orders",
            headers={"X-Aegis-Token": "test-token"},
        )
        assert response.status_code == 200


class TestPaperEndpoint403WithWrongToken:
    """Verify paper endpoints return 403 with wrong token."""

    def test_paper_endpoint_403_with_wrong_token(self, client: TestClient, monkeypatch) -> None:
        """GET /api/paper/orders should return 403 with wrong token."""
        monkeypatch.setattr(get_config(), "paper_token", "test-token")

        response = client.get(
            "/api/paper/orders",
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert response.status_code == 403


class TestDevModeAllowsUnauthenticated:
    """Verify paper endpoints allow unauthenticated access in DEVELOPMENT mode."""

    def test_dev_mode_allows_unauthenticated(self, client: TestClient, monkeypatch) -> None:
        """GET /api/paper/orders should return 200 in DEVELOPMENT with no token."""
        monkeypatch.setattr(get_config(), "paper_token", "")
        monkeypatch.setattr(get_config(), "profile", "DEVELOPMENT")

        response = client.get("/api/paper/orders")
        assert response.status_code == 200


class TestProductionModeRejectsUnconfiguredToken:
    """Verify paper endpoints reject in PRODUCTION when token is not configured."""

    def test_production_mode_rejects_unconfigured_token(self, client: TestClient, monkeypatch) -> None:
        """GET /api/paper/orders should return 401 in PRODUCTION with no token."""
        monkeypatch.setattr(get_config(), "paper_token", "")
        monkeypatch.setattr(get_config(), "profile", "PRODUCTION")

        response = client.get("/api/paper/orders")
        assert response.status_code == 401
        assert "production" in response.json()["detail"].lower()

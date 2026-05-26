"""Tests for health check endpoints."""

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


class TestHealthEndpoints:
    def test_backend_status_endpoint_returns_200(self):
        """GET /api/health returns 200 and status ok."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

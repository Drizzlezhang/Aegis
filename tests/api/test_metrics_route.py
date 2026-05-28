"""Integration tests for /metrics/prometheus HTTP endpoint."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a TestClient for the FastAPI app."""
    from src.api.main import app
    return TestClient(app)


class TestMetricsPrometheusEndpoint:
    """Verify GET /metrics/prometheus returns valid Prometheus text."""

    def test_returns_200_and_text_plain(self, client):
        """Endpoint returns 200 with Content-Type text/plain."""
        response = client.get("/api/metrics/prometheus")
        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")

    def test_response_contains_aegis_metrics(self, client):
        """Response body contains at least 10 aegis_* metric definitions."""
        response = client.get("/api/metrics/prometheus")
        lines = response.text.strip().split("\n")
        aegis_lines = [
            line for line in lines
            if "aegis_" in line
        ]
        assert len(aegis_lines) >= 10, (
            f"Expected >=10 aegis_* metric lines, got {len(aegis_lines)}"
        )

    def test_degraded_when_prometheus_client_missing(self, monkeypatch):
        """Returns degraded response (not 500) when prometheus_client is missing."""
        import src.api.routes.metrics as metrics_module

        original_import = __import__

        def mock_import(name, *args, **kwargs):
            if name == "src.services.metrics":
                raise ImportError("prometheus_client not installed")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        # Force re-import of the route module to pick up the mock
        import importlib
        importlib.reload(metrics_module)

        from src.api.main import app
        client2 = TestClient(app)
        response = client2.get("/api/metrics/prometheus")
        assert response.status_code == 200
        assert "prometheus_client not installed" in response.text.lower()

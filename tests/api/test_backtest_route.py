"""Tests for backtest v3 API endpoints."""

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


class TestBacktestV3API:
    """T15: Backtest v3 API endpoints — POST /backtest/runs, GET /backtest/runs, etc."""

    def test_submit_walkforward_run(self):
        """POST /api/backtest/runs submits a walk-forward run and returns run_id."""
        response = client.post("/api/backtest/runs", json={
            "symbol": "QQQ",
            "start_date": "2024-01-01",
            "end_date": "2024-03-31",
            "train_window_days": 60,
            "test_window_days": 15,
            "step_size_days": 15,
            "mode": "rolling",
        })
        assert response.status_code == 202
        data = response.json()
        assert "run_id" in data
        assert data["symbol"] == "QQQ"
        assert data["status"] == "completed"
        assert data["total_folds"] > 0

    def test_submit_walkforward_invalid_dates(self):
        """POST /api/backtest/runs returns 400 for invalid dates."""
        response = client.post("/api/backtest/runs", json={
            "symbol": "QQQ",
            "start_date": "2024-03-31",
            "end_date": "2024-01-01",
            "train_window_days": 60,
            "test_window_days": 15,
            "step_size_days": 15,
        })
        assert response.status_code == 400

    def test_list_walkforward_runs(self):
        """GET /api/backtest/runs returns list of runs."""
        # First submit a run
        client.post("/api/backtest/runs", json={
            "symbol": "QQQ",
            "start_date": "2024-01-01",
            "end_date": "2024-03-31",
            "train_window_days": 60,
            "test_window_days": 15,
            "step_size_days": 15,
        })

        response = client.get("/api/backtest/runs")
        assert response.status_code == 200
        data = response.json()
        assert "runs" in data
        assert len(data["runs"]) >= 1

    def test_list_walkforward_runs_filtered(self):
        """GET /api/backtest/runs?symbol=QQQ filters by symbol."""
        response = client.get("/api/backtest/runs", params={"symbol": "QQQ"})
        assert response.status_code == 200
        data = response.json()
        for run in data["runs"]:
            assert run["symbol"] == "QQQ"

    def test_get_walkforward_run(self):
        """GET /api/backtest/runs/{run_id} returns run details."""
        # Submit a run first
        submit_resp = client.post("/api/backtest/runs", json={
            "symbol": "QQQ",
            "start_date": "2024-01-01",
            "end_date": "2024-03-31",
            "train_window_days": 60,
            "test_window_days": 15,
            "step_size_days": 15,
        })
        run_id = submit_resp.json()["run_id"]

        response = client.get(f"/api/backtest/runs/{run_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == run_id
        assert data["symbol"] == "QQQ"
        assert "folds" in data
        assert "trades" in data

    def test_get_walkforward_run_not_found(self):
        """GET /api/backtest/runs/{run_id} returns 404 for non-existent run."""
        response = client.get("/api/backtest/runs/nonexistent123")
        assert response.status_code == 404

    def test_get_walkforward_report(self):
        """GET /api/backtest/runs/{run_id}/report returns HTML report."""
        # Submit a run first
        submit_resp = client.post("/api/backtest/runs", json={
            "symbol": "QQQ",
            "start_date": "2024-01-01",
            "end_date": "2024-03-31",
            "train_window_days": 60,
            "test_window_days": 15,
            "step_size_days": 15,
        })
        run_id = submit_resp.json()["run_id"]

        response = client.get(f"/api/backtest/runs/{run_id}/report")
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == run_id
        assert "html" in data
        assert "<html" in data["html"]
        assert "QQQ" in data["html"]

    def test_get_walkforward_report_not_found(self):
        """GET /api/backtest/runs/{run_id}/report returns 404 for non-existent run."""
        response = client.get("/api/backtest/runs/nonexistent123/report")
        assert response.status_code == 404

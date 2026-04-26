"""Tests for analysis history API endpoints."""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.agents.aegis_memory.storage import AnalysisStorage
from src.api.main import app

client = TestClient(app)


class TestGetAnalysisHistory:
    """Tests for GET /api/analysis."""

    def test_returns_empty_list_when_database_has_no_history(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".db") as temp_db:
            mock_config = MagicMock()
            mock_config.memory.sqlite_path = temp_db.name

            with patch("src.api.routes.analysis.get_config", return_value=mock_config):
                response = client.get("/api/analysis")

        assert response.status_code == 200
        assert response.json() == []

    def test_returns_404_when_analysis_detail_is_missing(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".db") as temp_db:
            mock_config = MagicMock()
            mock_config.memory.sqlite_path = temp_db.name

            with patch("src.api.routes.analysis.get_config", return_value=mock_config):
                response = client.get("/api/analysis/999")

        assert response.status_code == 404
        assert response.json() == {"detail": "Analysis not found"}

    def test_returns_analysis_detail_from_sqlite_storage(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".db") as temp_db:
            storage = AnalysisStorage(Path(temp_db.name))
            storage.ensure_schema()

            with sqlite3.connect(temp_db.name) as conn:
                conn.execute(
                    """
                    INSERT INTO analysis_results (
                        symbol, trade_date, agent_sequence, recommendations,
                        action_report, execution_time, success
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "QQQ",
                        "2026-04-26",
                        '["Data-Harvester", "Aegis-Memory"]',
                        '[{"type": "leaps_call"}]',
                        "Bullish setup near support",
                        1.23,
                        1,
                    ),
                )
                conn.commit()

            mock_config = MagicMock()
            mock_config.memory.sqlite_path = temp_db.name

            with patch("src.api.routes.analysis.get_config", return_value=mock_config):
                response = client.get("/api/analysis/1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["symbol"] == "QQQ"
        assert data["tradeDate"] == "2026-04-26"
        assert data["agentSequence"] == ["Data-Harvester", "Aegis-Memory"]
        assert data["recommendations"] == [{"type": "leaps_call"}]
        assert data["actionReport"] == "Bullish setup near support"
        assert data["executionTime"] == 1.23
        assert data["success"] is True
        assert isinstance(data["createdAt"], str)
        assert data["createdAt"]

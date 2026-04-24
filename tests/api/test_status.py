"""Tests for status API endpoint."""

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


class TestGetStatus:
    """Tests for GET /api/status."""

    def test_returns_200(self) -> None:
        response = client.get("/api/status")
        assert response.status_code == 200

    def test_has_agents(self) -> None:
        data = client.get("/api/status").json()
        assert "agents" in data
        assert isinstance(data["agents"], list)
        assert len(data["agents"]) == 4

    def test_agent_structure(self) -> None:
        data = client.get("/api/status").json()
        agent = data["agents"][0]
        assert "name" in agent
        assert "status" in agent
        assert "lastRun" in agent
        assert "executions" in agent

    def test_has_skills(self) -> None:
        data = client.get("/api/status").json()
        assert "skills" in data
        assert isinstance(data["skills"], list)

    def test_skill_structure(self) -> None:
        data = client.get("/api/status").json()
        skill = data["skills"][0]
        assert "name" in skill
        assert "type" in skill
        assert "loaded" in skill

    def test_has_system_info(self) -> None:
        data = client.get("/api/status").json()
        assert "system" in data
        system = data["system"]
        assert "version" in system
        assert "uptime" in system
        assert "memoryUsage" in system

    def test_has_health(self) -> None:
        data = client.get("/api/status").json()
        assert "health" in data
        health = data["health"]
        expected_keys = {
            "data_harvester",
            "quant_brain",
            "strategy_exec",
            "aegis_memory",
            "llm_router",
            "vector_store",
        }
        assert expected_keys.issubset(health.keys())
        for value in health.values():
            assert isinstance(value, bool)

    def test_all_healthy(self) -> None:
        data = client.get("/api/status").json()
        assert all(data["health"].values())

"""Tests for analyze API endpoint."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from src.api.main import app
from src.models import OptionContract, OptionType, RecommendedOption

client = TestClient(app)


class TestPostAnalyze:
    """Tests for POST /api/analyze."""

    def test_empty_symbols_returns_400(self) -> None:
        response = client.post("/api/analyze", json={"symbols": []})
        assert response.status_code == 400
        assert response.json() == {"detail": "No symbols provided"}

    def test_returns_503_when_orchestrator_is_not_initialized(self) -> None:
        with patch("src.api.routes.analyze._orchestrator", None):
            response = client.post("/api/analyze", json={"symbols": ["QQQ"]})

        assert response.status_code == 503
        assert response.json() == {"detail": "Analysis engine not initialized"}

    def test_returns_report_and_recommendations_from_state(self) -> None:
        contract = OptionContract(
            symbol="QQQ260116C00450000",
            underlying="QQQ",
            contract_symbol="QQQ260116C00450000",
            strike=450.0,
            expiry=date(2026, 1, 16),
            option_type=OptionType.CALL,
            last_price=12.5,
            bid=12.3,
            ask=12.7,
            volume=100,
            open_interest=200,
        )
        recommendation = RecommendedOption(
            contract=contract,
            recommendation_type="leaps_call",
            entry_price=12.5,
            target_price=20.0,
            stop_loss=8.0,
            risk_reward_ratio=1.6,
            confidence=0.756,
            reasoning="Support held and valuation improved",
        )
        state = SimpleNamespace(
            symbol="QQQ",
            action_report="Bullish setup near support",
            agent_sequence=["Data-Harvester", "Quant-Brain", "Aegis-Memory"],
            recommended_options=[recommendation],
        )
        orchestrator = AsyncMock()
        orchestrator.analyze_symbols.return_value = [state]

        with patch("src.api.routes.analyze._orchestrator", orchestrator):
            response = client.post("/api/analyze", json={"symbols": ["qqq"]})

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["totalTime"], float)
        assert len(data["results"]) == 1
        result = data["results"][0]
        assert result["symbol"] == "QQQ"
        assert result["status"] == "success"
        assert result["agentSequence"] == ["Data-Harvester", "Quant-Brain", "Aegis-Memory"]
        assert result["recommendationsCount"] == 1
        assert result["report"] == "Bullish setup near support"
        assert result["recommendations"] == [
            {
                "type": "leaps_call",
                "contractSymbol": "QQQ260116C00450000",
                "strike": 450.0,
                "expiry": "2026-01-16",
                "entryPrice": 12.5,
                "targetPrice": 20.0,
                "stopLoss": 8.0,
                "riskRewardRatio": 1.6,
                "confidence": 0.76,
                "reasoning": "Support held and valuation improved",
            }
        ]

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.orchestrator import Orchestrator
from src.models import AgentState


@pytest.mark.asyncio
async def test_non_critical_agent_failure_continues():
    orchestrator = Orchestrator()
    await orchestrator.initialize()

    with patch.object(
        orchestrator._agents.get("Aegis-Memory", AsyncMock()),
        'run',
        side_effect=RuntimeError("Mocked memory failure")
    ):
        state = AgentState(symbol="TEST", trade_date=date.today())
        # We need to provide a subset or mock the pipeline steps so it runs quickly
        # We'll just run the default pipeline
        state = await orchestrator._run_pipeline(state)

        # Should not have raised exception, and error should be recorded
        assert state is not None
        assert "Aegis-Memory" in state.metadata.get("agent_errors", {})
        assert "Mocked memory failure" in state.metadata["agent_errors"]["Aegis-Memory"]


@pytest.mark.asyncio
async def test_critical_agent_failure_aborts():
    orchestrator = Orchestrator()
    await orchestrator.initialize()

    with patch.object(
        orchestrator._agents.get("Data-Harvester", AsyncMock()),
        'run',
        side_effect=RuntimeError("Mocked critical failure")
    ):
        state = AgentState(symbol="TEST", trade_date=date.today())

        with pytest.raises(RuntimeError, match="Mocked critical failure"):
            await orchestrator._run_pipeline(state)

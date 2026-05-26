"""Tests for Orchestrator robustness: timeout, retry, semaphore."""

import asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.orchestrator import (
    AGENT_TIMEOUTS,
    CRITICAL_AGENTS,
    DEFAULT_AGENT_TIMEOUT,
    MAX_RETRIES,
    AgentTimeoutError,
    Orchestrator,
    PipelineStep,
)
from src.models import AgentState


def _make_step(agent_name: str, index: int = 1, total: int = 6) -> PipelineStep:
    return PipelineStep(index=index, total=total, display_name=agent_name, agent_name=agent_name)


def _make_state(symbol: str = "AAPL") -> AgentState:
    return AgentState(symbol=symbol, trade_date=date.today())


@pytest.mark.asyncio
async def test_agent_timeout_skips_non_critical():
    """Non-critical agent timeout should be recorded and pipeline continues."""
    orch = Orchestrator()
    step = _make_step("Aegis-Memory")
    state = _make_state()

    # Mock agent to timeout
    async def slow_run(_state):
        await asyncio.sleep(999)  # will be interrupted by wait_for
    orch._agents["Aegis-Memory"].run = slow_run

    # Override timeout to a tiny value for fast test
    with patch.object(orch, "_execute_agent_with_timeout", side_effect=AgentTimeoutError("Aegis-Memory", 0.001)):
        result = await orch._run_agent_with_retry(step, state)

    # Should have recorded the error
    assert "agent_errors" in state.metadata
    assert "Aegis-Memory" in state.metadata["agent_errors"]


@pytest.mark.asyncio
async def test_agent_timeout_raises_for_critical():
    """Critical agent (Data-Harvester) timeout should raise."""
    orch = Orchestrator()
    step = _make_step("Data-Harvester")
    state = _make_state()

    with patch.object(orch, "_execute_agent_with_timeout", side_effect=AgentTimeoutError("Data-Harvester", 0.001)):
        with pytest.raises(AgentTimeoutError):
            await orch._run_agent_with_retry(step, state)


@pytest.mark.asyncio
async def test_agent_retry_succeeds_on_second_attempt():
    """Non-critical agent should retry and succeed on second attempt."""
    orch = Orchestrator()
    step = _make_step("Quant-Brain")
    state = _make_state()

    call_count = [0]

    async def flaky_run(_state):
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("temporary failure")
        return _state

    orch._agents["Quant-Brain"].run = flaky_run

    result = await orch._run_agent_with_retry(step, state)

    assert call_count[0] == 2
    assert "agent_retries" in state.metadata
    assert len(state.metadata["agent_retries"]) == 1


@pytest.mark.asyncio
async def test_agent_retry_exhausted_skips():
    """Non-critical agent that fails all retries should be skipped."""
    orch = Orchestrator()
    step = _make_step("Position-Monitor")
    state = _make_state()

    async def always_fail(_state):
        raise RuntimeError("persistent failure")

    orch._agents["Position-Monitor"].run = always_fail

    result = await orch._run_agent_with_retry(step, state)

    # Should have recorded errors and retries
    assert "agent_errors" in state.metadata
    assert "Position-Monitor" in state.metadata["agent_errors"]
    assert "agent_retries" in state.metadata
    assert len(state.metadata["agent_retries"]) == MAX_RETRIES - 1  # first attempt + retries


@pytest.mark.asyncio
async def test_analyze_symbols_respects_semaphore():
    """analyze_symbols should not exceed max_concurrent_agents."""
    orch = Orchestrator()
    orch._config_dict["max_concurrent_agents"] = 2

    running = [0]
    max_seen = [0]

    async def tracked_analyze(symbol: str) -> AgentState:
        running[0] += 1
        max_seen[0] = max(max_seen[0], running[0])
        await asyncio.sleep(0.01)
        running[0] -= 1
        return _make_state(symbol)

    orch.analyze_symbol = tracked_analyze

    symbols = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN"]
    results = await orch.analyze_symbols(symbols)

    assert len(results) == 5
    assert max_seen[0] <= 2

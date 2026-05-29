"""E2E smoke test — 真实 yfinance 数据跑完整 pipeline。

用法: pytest tests/e2e/ -m e2e --run-e2e
默认跳过（需要网络 + yfinance）。
"""

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_E2E_TESTS"),
    reason="E2E tests disabled by default (set RUN_E2E_TESTS=1)"
)


@pytest.mark.live
@pytest.mark.asyncio
async def test_full_pipeline_single_symbol():
    """跑一个 symbol 的完整 pipeline，验证不 crash 且产出 recommendations。"""
    from src.agents.orchestrator import Orchestrator

    orchestrator = Orchestrator()
    await orchestrator.initialize()

    state = await orchestrator.analyze_symbol("NVDA")

    assert state is not None
    assert state.symbol == "NVDA"
    assert state.metadata.get("agent_timings") is not None
    assert state.metadata.get("trace_id") is not None
    # 至少应该有技术分析结果
    assert state.analysis_report or state.metadata.get("technical_summary")


@pytest.mark.live
@pytest.mark.asyncio
async def test_pipeline_graceful_degradation():
    """验证非 critical agent 失败时 pipeline 不中断。"""
    from unittest.mock import AsyncMock, patch

    from src.agents.orchestrator import Orchestrator

    orchestrator = Orchestrator()
    await orchestrator.initialize()

    # Mock memory agent 失败
    with patch.object(
        orchestrator._agents.get("Aegis-Memory", AsyncMock()),
        'run',
        side_effect=RuntimeError("Memory unavailable")
    ):
        state = await orchestrator.analyze_symbol("SPY")

    assert state is not None
    assert "Aegis-Memory" in state.metadata.get("agent_errors", {})

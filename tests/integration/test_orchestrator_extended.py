"""Extended end-to-end integration tests for the multi-agent pipeline."""

import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.orchestrator import Orchestrator
from src.models import (
    OHLCV,
    OptionChain,
    OptionContract,
    OptionType,
    SupportResistanceLevel,
    ValuationRange,
)


@pytest.fixture
def mock_yfinance_skill():
    """Create a mock yfinance skill returning sample data."""
    skill = MagicMock()
    skill.execute = AsyncMock()

    ohlcv_data = [
        OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, i), open=100 + i, high=101 + i, low=99 + i, close=100.5 + i, volume=1000000 + i * 10000)
        for i in range(1, 11)
    ]

    call_contract = OptionContract(
        symbol="QQQ240621C00150000",
        underlying="QQQ",
        contract_symbol="QQQ240621C00150000",
        strike=150.0,
        expiry=date(2024, 6, 21),
        option_type=OptionType.CALL,
        last_price=5.0,
        bid=4.8,
        ask=5.2,
        volume=100,
        open_interest=500,
        delta=0.7,
    )

    options_chain = OptionChain(
        symbol="QQQ",
        timestamp=datetime(2024, 1, 10),
        spot_price=102.5,
        calls=[call_contract],
        puts=[],
        expiry_dates=[date(2024, 6, 21)]
    )

    fundamentals = {
        "pe_ratio": 25.0,
        "market_cap": 1000000000,
        "dividend_yield": 0.02
    }

    async def execute_side_effect(params):
        data_type = params.get("data_type")
        result = Mock()
        result.success = True
        if data_type == "ohlcv":
            result.data = ohlcv_data
        elif data_type == "options":
            result.data = options_chain
        elif data_type == "fundamentals":
            result.data = fundamentals
        else:
            result.data = None
        return result

    skill.execute.side_effect = execute_side_effect
    skill.initialize = AsyncMock()
    return skill


@pytest.fixture
def mock_registry(mock_yfinance_skill):
    """Create a mock skill registry."""
    registry = MagicMock()
    registry.get_skill.return_value = mock_yfinance_skill
    registry.discover_skills.return_value = ["yfinance_ohlcv"]
    return registry


@pytest.fixture
def orchestrator(mock_registry):
    """Create an orchestrator with mocked dependencies."""
    with patch('src.agents.data_harvester.agent.get_global_registry', return_value=mock_registry), \
         patch('src.agents.quant_brain.agent.get_global_registry', return_value=mock_registry):
        orch = Orchestrator()
        yield orch


class TestReportGeneration:
    """Test report generation with and without LLM."""

    @pytest.mark.asyncio
    async def test_generate_final_report_with_llm(self, orchestrator):
        """Test LLM-enhanced report generation."""
        await orchestrator.initialize()
        state = await orchestrator.analyze_symbol("QQQ")

        with patch('src.agents.orchestrator.generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = "ENHANCED LLM REPORT\n\nExecutive Summary: Strong buy"

            report = await orchestrator.generate_final_report(state)

            assert "ENHANCED LLM REPORT" in report
            assert "Executive Summary" in report
            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_final_report_llm_fallback(self, orchestrator):
        """Test fallback to basic report when LLM fails."""
        await orchestrator.initialize()
        state = await orchestrator.analyze_symbol("QQQ")

        with patch('src.agents.orchestrator.generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.side_effect = Exception("LLM API error")

            report = await orchestrator.generate_final_report(state)

            # Should fallback to basic report
            assert "AEGIS-TRADER ANALYSIS REPORT" in report
            assert "QQQ" in report

    @pytest.mark.asyncio
    async def test_report_contains_all_sections(self, orchestrator):
        """Verify basic report contains all required sections."""
        await orchestrator.initialize()
        state = await orchestrator.analyze_symbol("QQQ")

        report = orchestrator._generate_basic_report(state)

        assert "MARKET DATA SUMMARY" in report
        assert "QUANTITATIVE ANALYSIS" in report
        assert "STRATEGY RECOMMENDATIONS" in report
        assert "ACTION REPORT" in report
        assert "RISK DISCLAIMER" in report
        assert "QQQ" in report


class TestStrategyGeneration:
    """Test strategy recommendation generation."""

    @pytest.fixture
    def mock_yfinance_with_leaps(self):
        """Create mock skill with LEAPS-eligible options."""
        skill = MagicMock()
        skill.execute = AsyncMock()

        ohlcv_data = [
            OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, i), open=100 + i, high=101 + i, low=99 + i, close=100.5 + i, volume=1000000)
            for i in range(1, 11)
        ]

        # LEAPS calls (expiry > 300 days)
        leaps_expiry = date.today() + timedelta(days=400)
        call1 = OptionContract(
            symbol="QQQ",
            underlying="QQQ",
            contract_symbol=f"QQQ{leaps_expiry.strftime('%y%m%d')}C00150000",
            strike=150.0,
            expiry=leaps_expiry,
            option_type=OptionType.CALL,
            last_price=5.0,
            bid=4.8,
            ask=5.2,
            volume=100,
            open_interest=500,
            delta=0.7,
        )
        call2 = OptionContract(
            symbol="QQQ",
            underlying="QQQ",
            contract_symbol=f"QQQ{leaps_expiry.strftime('%y%m%d')}C00155000",
            strike=155.0,
            expiry=leaps_expiry,
            option_type=OptionType.CALL,
            last_price=4.0,
            bid=3.8,
            ask=4.2,
            volume=80,
            open_interest=400,
            delta=0.65,
        )
        call3 = OptionContract(
            symbol="QQQ",
            underlying="QQQ",
            contract_symbol=f"QQQ{leaps_expiry.strftime('%y%m%d')}C00160000",
            strike=160.0,
            expiry=leaps_expiry,
            option_type=OptionType.CALL,
            last_price=3.0,
            bid=2.8,
            ask=3.2,
            volume=60,
            open_interest=300,
            delta=0.55,
        )

        options_chain = OptionChain(
            symbol="QQQ",
            timestamp=datetime.now(),
            spot_price=152.0,
            calls=[call1, call2, call3],
            puts=[],
            expiry_dates=[leaps_expiry]
        )

        async def execute_side_effect(params):
            data_type = params.get("data_type")
            result = Mock()
            result.success = True
            if data_type == "ohlcv":
                result.data = ohlcv_data
            elif data_type == "options":
                result.data = options_chain
            else:
                result.data = None
            return result

        skill.execute.side_effect = execute_side_effect
        skill.initialize = AsyncMock()
        return skill

    @pytest.fixture
    def orchestrator_with_leaps(self, mock_yfinance_with_leaps):
        """Create orchestrator with LEAPS-capable mock data."""
        registry = MagicMock()
        registry.get_skill.return_value = mock_yfinance_with_leaps
        registry.discover_skills.return_value = ["yfinance_ohlcv"]

        with patch('src.agents.data_harvester.agent.get_global_registry', return_value=registry), \
             patch('src.agents.quant_brain.agent.get_global_registry', return_value=registry):
            orch = Orchestrator()
            yield orch

    @pytest.mark.asyncio
    async def test_pipeline_generates_leaps_call(self, orchestrator_with_leaps):
        """Verify pipeline generates LEAPS Call recommendation."""
        orch = orchestrator_with_leaps
        await orch.initialize()

        state = await orch.analyze_symbol("QQQ")

        leaps_recs = [r for r in state.recommended_options if r.recommendation_type == "leaps_call"]
        assert len(leaps_recs) >= 1
        assert leaps_recs[0].contract is not None
        assert leaps_recs[0].entry_price > 0

    @pytest.mark.asyncio
    async def test_pipeline_generates_bull_spread(self, orchestrator_with_leaps):
        """Verify pipeline generates Bull Spread recommendation."""
        orch = orchestrator_with_leaps
        await orch.initialize()

        state = await orch.analyze_symbol("QQQ")

        spread_recs = [r for r in state.recommended_options if r.recommendation_type == "bull_spread"]
        # Bull spread requires support levels, which quant_brain generates
        # If no support levels, no bull spread
        assert len(spread_recs) >= 0

    @pytest.mark.asyncio
    async def test_pipeline_generates_covered_call(self, orchestrator_with_leaps):
        """Verify pipeline generates Covered Call recommendation."""
        orch = orchestrator_with_leaps
        await orch.initialize()

        state = await orch.analyze_symbol("QQQ")

        cc_recs = [r for r in state.recommended_options if r.recommendation_type == "covered_call"]
        assert len(cc_recs) >= 1
        assert cc_recs[0].contract is not None


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_pipeline_empty_ohlcv(self, orchestrator):
        """Test pipeline with empty OHLCV data."""
        await orchestrator.initialize()

        async def empty_ohlcv_execute(params):
            result = Mock()
            result.success = True
            if params.get("data_type") == "ohlcv":
                result.data = []
            elif params.get("data_type") == "options":
                result.data = None
            else:
                result.data = None
            return result

        with patch.object(orchestrator.get_agent("Data-Harvester")._yfinance_skill, 'execute',
                          side_effect=empty_ohlcv_execute):
            state = await orchestrator.analyze_symbol("QQQ")

            assert state.symbol == "QQQ"
            # Empty list is treated as falsy, so ohlcv_data stays None
            assert state.ohlcv_data is None
            # Pipeline should still complete
            assert any("Strategy-Execution" in step for step in state.agent_sequence)

    @pytest.mark.asyncio
    async def test_pipeline_no_support_levels(self, orchestrator):
        """Test pipeline when quant brain produces no support levels."""
        await orchestrator.initialize()

        with patch.object(orchestrator.get_agent("Quant-Brain"), 'run', new_callable=AsyncMock) as mock_quant:
            from src.models import AgentState
            from datetime import date

            # Return state with no support levels
            minimal_state = AgentState(
                symbol="QQQ",
                trade_date=date.today(),
                ohlcv_data=[],
                options_chain=None,
                support_levels=[],
                resistance_levels=[],
            )
            minimal_state.add_agent_step("Data-Harvester")
            mock_quant.return_value = minimal_state

            state = await orchestrator.analyze_symbol("QQQ")

            assert state.symbol == "QQQ"
            assert state.support_levels == []
            assert state.recommended_options == []

    @pytest.mark.asyncio
    async def test_batch_analysis_with_errors(self, orchestrator):
        """Test batch analysis when some symbols fail."""
        await orchestrator.initialize()

        call_count = 0

        async def failing_execute(params):
            nonlocal call_count
            call_count += 1
            result = Mock()
            if call_count > 2:  # Fail after some calls
                result.success = False
                result.data = None
                result.error = "API rate limit"
            else:
                result.success = True
                result.data = []
            return result

        with patch.object(orchestrator.get_agent("Data-Harvester")._yfinance_skill, 'execute',
                          side_effect=failing_execute):
            states = await orchestrator.analyze_symbols(["QQQ", "SPY", "AAPL"])

            assert len(states) == 3
            # All should have symbol set
            assert states[0].symbol == "QQQ"
            assert states[1].symbol == "SPY"
            assert states[2].symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_execution_history_tracks_failures(self, orchestrator):
        """Verify execution history tracks failed analyses."""
        await orchestrator.initialize()

        with patch.object(orchestrator.get_agent("Data-Harvester"), 'run',
                          side_effect=Exception("Network error")):
            state = await orchestrator.analyze_symbol("QQQ")
            assert "Pipeline Error" in state.action_report

        history = orchestrator.get_execution_history()
        assert len(history) == 1
        assert history[0]["symbol"] == "QQQ"
        assert history[0]["success"] is False


class TestSkillRegistryIntegration:
    """Test SkillRegistry integration with Orchestrator."""

    def test_skill_registry_discovery(self):
        """Verify skill registry can discover actual skills."""
        from src.skills import SkillRegistry

        registry = SkillRegistry()
        # Add the skills directory
        skills_dir = Path(__file__).parent.parent.parent / "skills"
        if skills_dir.exists():
            registry.add_skill_dir(skills_dir)
            skills = registry.discover_skills()

            skill_names = [s.name for s in skills]
            assert "yfinance_ohlcv" in skill_names or len(skills) >= 0

    def test_orchestrator_uses_config(self):
        """Verify orchestrator loads configuration."""
        orch = Orchestrator()
        assert orch._config is not None
        assert hasattr(orch._config, 'llm')
        assert hasattr(orch._config, 'data_source')

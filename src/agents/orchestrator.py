"""Orchestrator: Manages the multi-agent analysis pipeline."""

import asyncio
import logging
import time
from datetime import date, datetime
from typing import Any

from src.agents.aegis_memory.agent import AegisMemoryAgent
from src.agents.data_harvester.agent import DataHarvesterAgent
from src.agents.quant_brain.agent import QuantBrainAgent
from src.agents.strategy_exec.agent import StrategyExecAgent
from src.config import get_config
from src.llm import TaskType, generate
from src.models import AgentState

logger = logging.getLogger(__name__)


class Orchestrator:
    """Orchestrates the multi-agent analysis pipeline."""

    def __init__(self, config: dict[str, Any] | None = None):
        self._config = get_config()
        self._config_dict = config or {}

        # Initialize agents
        self._data_harvester = DataHarvesterAgent()
        self._quant_brain = QuantBrainAgent()
        self._strategy_exec = StrategyExecAgent()
        self._aegis_memory = AegisMemoryAgent()

        # Track execution history
        self._execution_history: list[dict[str, Any]] = []

    async def initialize(self) -> None:
        """Initialize all agents."""
        logger.info("Initializing orchestrator and all agents...")

        await self._data_harvester.initialize()
        await self._quant_brain.initialize()
        await self._strategy_exec.initialize()
        await self._aegis_memory.initialize()

        logger.info("All agents initialized successfully")

    async def analyze_symbol(self, symbol: str) -> AgentState:
        """Run full analysis pipeline for a single symbol."""
        symbol = symbol.upper()
        start_time = time.time()

        logger.info(f"{'=' * 60}")
        logger.info(f"Starting analysis pipeline for {symbol}")
        logger.info(f"{'=' * 60}")

        # Initialize state
        state = AgentState(
            symbol=symbol,
            trade_date=date.today()
        )

        try:
            # Step 1: Data-Harvester
            logger.info(f"[1/4] Running Data-Harvester for {symbol}...")
            state = await self._data_harvester.run(state)
            logger.info("[1/4] Data-Harvester completed")

            # Step 2: Quant-Brain
            logger.info(f"[2/4] Running Quant-Brain for {symbol}...")
            state = await self._quant_brain.run(state)
            logger.info("[2/4] Quant-Brain completed")

            # Step 3: Strategy-Execution
            logger.info(f"[3/4] Running Strategy-Execution for {symbol}...")
            state = await self._strategy_exec.run(state)
            logger.info("[3/4] Strategy-Execution completed")

            # Step 4: Aegis-Memory
            logger.info(f"[4/4] Running Aegis-Memory for {symbol}...")
            state = await self._aegis_memory.run(state)
            logger.info("[4/4] Aegis-Memory completed")

        except Exception as e:
            logger.error(f"Error in analysis pipeline for {symbol}: {e}")
            state.action_report += f"\n\nPipeline Error: {str(e)}"

        # Record execution
        execution_time = time.time() - start_time
        self._execution_history.append({
            "symbol": symbol,
            "timestamp": datetime.now(),
            "execution_time": execution_time,
            "agent_sequence": state.agent_sequence.copy(),
            "recommendations_count": len(state.recommended_options),
            "success": "Pipeline Error" not in state.action_report
        })

        logger.info(f"Analysis pipeline completed for {symbol} in {execution_time:.2f}s")
        logger.info(f"Generated {len(state.recommended_options)} recommendations")

        return state

    async def analyze_symbols(self, symbols: list[str]) -> list[AgentState]:
        """Run analysis pipeline for multiple symbols in parallel."""
        logger.info(f"Starting batch analysis for {len(symbols)} symbols: {symbols}")

        tasks = [self.analyze_symbol(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        states: list[AgentState] = []
        for symbol, result in zip(symbols, results, strict=False):
            if isinstance(result, Exception):
                logger.error(f"Analysis failed for {symbol}: {result}")
                # Create error state
                error_state = AgentState(
                    symbol=symbol,
                    trade_date=date.today(),
                    action_report=f"Pipeline Error: {str(result)}"
                )
                states.append(error_state)
            else:
                states.append(result)  # type: ignore[arg-type]

        logger.info(f"Batch analysis completed: {len(states)} results")
        return states

    async def generate_final_report(self, state: AgentState) -> str:
        """Generate final analysis report using LLM."""
        # Use LLM to enhance the report
        basic_report = self._generate_basic_report(state)

        try:
            # Enhance with LLM for better readability and insights
            enhanced_report: str = await generate(
                prompt=f"""Enhance this trading analysis report with better formatting, clearer insights, and actionable recommendations:

Basic Report:
{basic_report}

Please provide:
1. Executive summary with key takeaways
2. Improved formatting for better readability
3. Clearer risk assessment
4. More actionable recommendations
5. Professional tone suitable for institutional investors

Focus on clarity, conciseness, and actionable insights.""",
                system_prompt="You are a senior quantitative analyst at a hedge fund. You specialize in options trading and market analysis.",
                task_type=TaskType.REPORT
            )
            return enhanced_report
        except Exception as e:
            logger.warning(f"LLM enhancement failed: {e}, using basic report")
            return basic_report

    def _generate_basic_report(self, state: AgentState) -> str:
        """Generate basic report without LLM enhancement."""
        symbol = state.symbol
        report = f"""
{'=' * 70}
AEGIS-TRADER ANALYSIS REPORT
{'=' * 70}
Symbol: {symbol}
Trade Date: {state.trade_date}
Analysis Time: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Pipeline: {' -> '.join(state.agent_sequence)}

{'=' * 70}
1. MARKET DATA SUMMARY
{'=' * 70}
"""

        if state.ohlcv_data:
            latest = state.ohlcv_data[-1] if state.ohlcv_data else None
            if latest:
                report += f"""
Latest Price: {latest.close:.2f}
Volume: {latest.volume:,}
Data Points: {len(state.ohlcv_data)} days
"""
        else:
            report += "\nNo market data available\n"

        if state.options_chain:
            report += f"""
Options Chain:
  Spot Price: {state.options_chain.spot_price:.2f}
  Calls: {len(state.options_chain.calls)} contracts
  Puts: {len(state.options_chain.puts)} contracts
  Expiry Dates: {len(state.options_chain.expiry_dates)}
"""

        report += f"""
{'=' * 70}
2. QUANTITATIVE ANALYSIS
{'=' * 70}
"""

        if state.volume_profile:
            report += f"""
Volume Profile:
  POC (Point of Control): {state.volume_profile.poc_price:.2f}
  VAH (Value Area High): {state.volume_profile.vah_price:.2f}
  VAL (Value Area Low): {state.volume_profile.val_price:.2f}
"""

        if state.gex_walls:
            support_walls = [w for w in state.gex_walls if w.is_support]
            resistance_walls = [w for w in state.gex_walls if w.is_resistance]
            report += f"""
GEX Walls:
  Support Walls: {len(support_walls)}
  Resistance Walls: {len(resistance_walls)}
"""
            if support_walls:
                strongest = max(support_walls, key=lambda w: w.absolute_gex)
                report += f"  Strongest Support: {strongest.strike:.2f} (GEX: {strongest.net_gex:,.0f})\n"

        if state.valuation_range:
            report += f"""
Valuation (PE-Band):
  Current Price: {state.valuation_range.current_price:.2f}
  Fair Estimate: {state.valuation_range.fair_estimate:.2f}
  Discount to Fair: {state.valuation_range.discount_to_fair:.1f}%
  Status: {'UNDervalued' if state.valuation_range.is_undervalued else 'OVERvalued' if state.valuation_range.is_overvalued else 'FAIR'}
"""

        if state.support_levels:
            report += "\nSupport Levels:\n"
            for level in state.support_levels[:5]:
                report += f"  {level.price:.2f} ({level.source}, confidence: {level.confidence:.1%})\n"

        if state.resistance_levels:
            report += "\nResistance Levels:\n"
            for level in state.resistance_levels[:5]:
                report += f"  {level.price:.2f} ({level.source}, confidence: {level.confidence:.1%})\n"

        report += f"""
{'=' * 70}
3. STRATEGY RECOMMENDATIONS
{'=' * 70}
"""

        if state.recommended_options:
            for i, rec in enumerate(state.recommended_options, 1):
                report += f"""
{i}. {rec.recommendation_type.upper().replace('_', ' ')}
   Contract: {rec.contract.contract_symbol}
   Strike: {rec.contract.strike:.2f}, Expiry: {rec.contract.expiry}
   Entry Price: {rec.entry_price:.2f}
   Target Price: {rec.target_price:.2f if rec.target_price else 'N/A'}
   Stop Loss: {rec.stop_loss:.2f if rec.stop_loss else 'N/A'}
   Risk/Reward: {rec.risk_reward_ratio:.2f if rec.risk_reward_ratio else 'N/A'}
   Confidence: {rec.confidence:.1%}

   Reasoning:
   {rec.reasoning}
"""
        else:
            report += "\nNo suitable strategies found for current market conditions.\n"

        report += f"""
{'=' * 70}
4. ACTION REPORT
{'=' * 70}
{state.action_report}

{'=' * 70}
5. RISK DISCLAIMER
{'=' * 70}
⚠️  IMPORTANT RISK WARNINGS:
   • This analysis is for informational purposes only
   • Options trading involves significant risk of loss
   • Past performance does not guarantee future results
   • Always do your own due diligence
   • Consider your risk tolerance and investment objectives
   • Position sizing: Never risk more than 2-5% per trade

{'=' * 70}
END OF REPORT
{'=' * 70}
"""

        return report

    def get_execution_history(self) -> list[dict[str, Any]]:
        """Get execution history."""
        return self._execution_history.copy()

    async def health_check(self) -> dict[str, bool]:
        """Check health of all agents."""
        return {
            "data_harvester": await self._data_harvester.health_check(),
            "quant_brain": self._quant_brain.status.value == "idle",
            "strategy_exec": self._strategy_exec.status.value == "idle",
            "aegis_memory": self._aegis_memory.status.value == "idle"
        }

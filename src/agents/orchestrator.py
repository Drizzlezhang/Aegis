"""Orchestrator: Manages the multi-agent analysis pipeline."""

import asyncio
import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from importlib import import_module
from typing import Any

from src.agents.base import BaseAgent
from src.agents.quant_brain.report_templates import FULL_ANALYSIS, build_structured_report
from src.config import get_config
from src.llm import generate
from src.models import AgentState
from src.observability.logging import TraceContext
from src.observability.metrics import PipelineMetrics

logger = logging.getLogger(__name__)

DEFAULT_PIPELINE = [
    ("Data-Harvester", "src.agents.data_harvester.agent", "DataHarvesterAgent"),
    ("Quant-Brain", "src.agents.quant_brain.agent", "QuantBrainAgent"),
    ("Investment-Debate", "src.agents.debate.agent", "DebateAgent"),
    ("Strategy-Execution", "src.agents.strategy_exec.agent", "StrategyExecAgent"),
    ("Aegis-Memory", "src.agents.aegis_memory.agent", "AegisMemoryAgent"),
    ("Position-Monitor", "src.agents.position_monitor.agent", "PositionMonitorAgent"),
]

# ── Timeout / Retry Configuration ──────────────────────────────────────────
DEFAULT_AGENT_TIMEOUT = 60  # seconds
AGENT_TIMEOUTS: dict[str, int] = {
    "Data-Harvester": 90,
    "Quant-Brain": 120,
    "Investment-Debate": 120,
    "Strategy-Execution": 60,
    "Aegis-Memory": 30,
    "Position-Monitor": 30,
}
CRITICAL_AGENTS: set[str] = {"Data-Harvester"}
MAX_RETRIES = 2
RETRY_BACKOFF_BASE = 1.0  # seconds


class AgentTimeoutError(Exception):
    """Raised when an agent exceeds its execution timeout."""

    def __init__(self, agent_name: str, timeout: float):
        self.agent_name = agent_name
        self.timeout = timeout
        super().__init__(f"{agent_name} timed out after {timeout}s")


@dataclass(frozen=True)
class PipelineStep:
    index: int
    total: int
    display_name: str
    agent_name: str


class Orchestrator:
    """Orchestrates the multi-agent analysis pipeline."""

    def __init__(self, config: dict[str, Any] | None = None):
        self._config = get_config()
        self._config_dict = config or {}
        self._agents: dict[str, BaseAgent] = {}
        self._pipeline_order: list[str] = []
        self._listeners: dict[str, list[Callable[..., Any]]] = {
            "pipeline_started": [],
            "step_started": [],
            "step_completed": [],
            "pipeline_completed": [],
        }
        self._execution_history: list[dict[str, Any]] = []
        self.metrics = PipelineMetrics()
        self.historical_mode: bool = False
        self._historical_data: dict[str, list[Any]] = {}

        for agent_name, module_path, class_name in DEFAULT_PIPELINE:
            self.register_agent(agent_name, module_path, class_name)

    def register_agent(self, agent_name: str, module_path: str, class_name: str) -> None:
        module = import_module(module_path)
        agent_class = getattr(module, class_name)
        agent = agent_class(self._config_dict)
        self._agents[agent_name] = agent
        if agent_name not in self._pipeline_order:
            self._pipeline_order.append(agent_name)

    def unregister_agent(self, agent_name: str) -> None:
        self._agents.pop(agent_name, None)
        self._pipeline_order = [name for name in self._pipeline_order if name != agent_name]

    def add_listener(self, event_name: str, listener: Callable[..., Any]) -> None:
        self._listeners.setdefault(event_name, []).append(listener)

    def remove_listener(self, event_name: str, listener: Callable[..., Any]) -> None:
        listeners = self._listeners.get(event_name, [])
        self._listeners[event_name] = [item for item in listeners if item != listener]

    async def _emit(self, event_name: str, **payload: Any) -> None:
        for listener in self._listeners.get(event_name, []):
            result = listener(**payload)
            if asyncio.iscoroutine(result):
                await result

    def get_agent(self, agent_name: str) -> BaseAgent | None:
        return self._agents.get(agent_name)

    def set_historical_data(self, symbol: str, ohlcv_window: list[Any]) -> None:
        """Inject historical OHLCV data for backtest mode.

        When historical_mode is True, DataHarvester reads from this
        cache instead of making HTTP calls.
        """
        self._historical_data[symbol.upper()] = ohlcv_window

    def get_historical_data(self, symbol: str) -> list[Any]:
        """Get injected historical data for a symbol."""
        return self._historical_data.get(symbol.upper(), [])

    def _build_pipeline_steps(self) -> list[PipelineStep]:
        total = len(self._pipeline_order)
        return [
            PipelineStep(index=index, total=total, display_name=agent_name, agent_name=agent_name)
            for index, agent_name in enumerate(self._pipeline_order, start=1)
        ]

    async def initialize(self) -> None:
        """Initialize all agents."""
        logger.info("Initializing orchestrator and all agents...")

        for step in self._build_pipeline_steps():
            agent = self._agents[step.agent_name]
            await agent.initialize()

        logger.info("All agents initialized successfully")

    async def analyze_symbol(self, symbol: str) -> AgentState:
        """Run full analysis pipeline for a single symbol."""
        symbol = symbol.upper()
        start_time = time.time()

        trace_id = str(uuid.uuid4())[:8]
        TraceContext.set(trace_id, symbol)
        logger.info("Pipeline started", extra={"extra_fields": {"trace_id": trace_id, "symbol": symbol}})

        logger.info(f"{'=' * 60}")
        logger.info(f"Starting analysis pipeline for {symbol}")
        logger.info(f"{'=' * 60}")

        pipeline_steps = self._build_pipeline_steps()
        state = AgentState(symbol=symbol, trade_date=date.today())
        state.total_steps = len(pipeline_steps)

        await self._emit("pipeline_started", symbol=symbol, state=state)

        try:
            state = await self._run_pipeline(state, pipeline_steps, trace_id)
            self._attach_structured_report(state)
        except Exception as e:
            logger.error(f"Error in analysis pipeline for {symbol}: {e}")
            state.action_report += f"\n\nPipeline Error: {str(e)}"

        execution_time = time.time() - start_time
        self._execution_history.append({
            "symbol": symbol,
            "timestamp": datetime.now(UTC),
            "execution_time": execution_time,
            "agent_sequence": state.agent_sequence.copy(),
            "recommendations_count": len(state.recommended_options),
            "success": "Pipeline Error" not in state.action_report,
        })

        await self._emit(
            "pipeline_completed",
            symbol=symbol,
            state=state,
            execution_time=execution_time,
        )

        logger.info(f"Analysis pipeline completed for {symbol} in {execution_time:.2f}s")
        logger.info(f"Generated {len(state.recommended_options)} recommendations")

        return state

    async def _execute_agent_with_timeout(self, agent: BaseAgent, state: AgentState, timeout: float) -> AgentState:
        """Execute agent with timeout protection."""
        try:
            return await asyncio.wait_for(
                agent.run(state),
                timeout=timeout,
            )
        except TimeoutError as e:
            raise AgentTimeoutError(agent.name, timeout) from e

    async def _run_agent_with_retry(self, step: PipelineStep, state: AgentState, request_id: str = "") -> AgentState:
        """Run agent with retry for non-critical agents."""
        agent = self._agents[step.agent_name]
        timeout = AGENT_TIMEOUTS.get(step.agent_name, DEFAULT_AGENT_TIMEOUT)
        is_critical = step.agent_name in CRITICAL_AGENTS

        for attempt in range(MAX_RETRIES):
            try:
                result = await self._execute_agent_with_timeout(agent, state, timeout)
                return result
            except AgentTimeoutError as e:
                state.metadata.setdefault("agent_errors", {})[step.agent_name] = str(e)
                if is_critical:
                    raise
                if attempt == MAX_RETRIES - 1:
                    # Non-critical: exhausted retries, skip agent
                    return state
                backoff = RETRY_BACKOFF_BASE * (2 ** attempt)
                state.metadata.setdefault("agent_retries", []).append({
                    "agent": step.agent_name,
                    "attempt": attempt + 1,
                    "error": str(e),
                })
                if request_id:
                    await self._emit("pipeline_progress",
                        request_id=request_id,
                        step={"index": step.index - 1, "total": step.total,
                              "agent": step.agent_name, "status": "retrying",
                              "attempt": attempt + 1})
                await asyncio.sleep(backoff)
            except Exception as e:
                state.metadata.setdefault("agent_errors", {})[step.agent_name] = str(e)
                if is_critical:
                    raise
                if attempt == MAX_RETRIES - 1:
                    # Non-critical: exhausted retries, skip agent
                    return state
                backoff = RETRY_BACKOFF_BASE * (2 ** attempt)
                state.metadata.setdefault("agent_retries", []).append({
                    "agent": step.agent_name,
                    "attempt": attempt + 1,
                    "error": str(e),
                })
                if request_id:
                    await self._emit("pipeline_progress",
                        request_id=request_id,
                        step={"index": step.index - 1, "total": step.total,
                              "agent": step.agent_name, "status": "retrying",
                              "attempt": attempt + 1})
                await asyncio.sleep(backoff)

        return state  # non-critical exhausted all retries

    async def _run_pipeline(self, state: AgentState, pipeline_steps: list[PipelineStep] | None = None, request_id: str = "") -> AgentState:
        """执行 pipeline，支持单 agent 失败时 graceful degradation。"""
        steps = pipeline_steps or self._build_pipeline_steps()
        agent_timings = {}
        checkpoints = []

        for step in steps:
            state.current_step = step.index - 1
            step_start = time.time()

            # 保存 checkpoint（浅拷贝 state）
            checkpoints.append({
                "agent": step.display_name,
                "state_snapshot": state.model_copy(deep=False) if hasattr(state, 'model_copy') else None,
            })

            logger.info(f"[{step.index}/{step.total}] Running {step.display_name} for {state.symbol}...")
            await self._emit("step_started", step=step, state=state)
            if request_id:
                await self._emit("pipeline_progress",
                    request_id=request_id,
                    step={"index": step.index - 1, "total": step.total,
                          "agent": step.display_name, "status": "started"})

            try:
                state = await self._run_agent_with_retry(step, state, request_id)
            except (AgentTimeoutError, Exception) as e:
                elapsed = time.time() - step_start
                elapsed_ms = elapsed * 1000
                is_timeout = isinstance(e, AgentTimeoutError)
                logger.error(f"Agent {step.display_name} failed: {e}",
                            extra={"extra_fields": {"agent": step.display_name, "error": str(e)}})
                agent_timings[step.display_name] = {"duration_s": round(elapsed, 3), "error": str(e)}

                # Record metrics
                self.metrics.record_agent_run(
                    step.display_name, success=False, duration_ms=elapsed_ms,
                    timeout=is_timeout,
                    retried=bool(state.metadata.get("agent_retries")),
                )

                if request_id:
                    await self._emit("pipeline_progress",
                        request_id=request_id,
                        step={"index": step.index - 1, "total": step.total,
                              "agent": step.display_name, "status": "failed",
                              "elapsed_ms": int(elapsed_ms)})

                # Non-critical agents 可以跳过，critical 必须中断
                if step.agent_name in CRITICAL_AGENTS:
                    raise
                # 其他 agent 失败 → 记录错误，继续 pipeline
                state.metadata.setdefault("agent_errors", {})[step.display_name] = str(e)
                continue

            elapsed = time.time() - step_start
            elapsed_ms = elapsed * 1000
            agent_timings[step.display_name] = {"duration_s": round(elapsed, 3), "status": "ok"}

            # Record metrics
            self.metrics.record_agent_run(
                step.display_name, success=True, duration_ms=elapsed_ms,
                retried=bool(state.metadata.get("agent_retries")),
            )

            state.current_step = step.index
            await self._emit("step_completed", step=step, state=state)
            if request_id:
                await self._emit("pipeline_progress",
                    request_id=request_id,
                    step={"index": step.index - 1, "total": step.total,
                          "agent": step.display_name, "status": "completed",
                          "elapsed_ms": int(elapsed_ms)})
            logger.info(f"[{step.index}/{step.total}] {step.display_name} completed in {elapsed:.2f}s",
                       extra={"extra_fields": {"agent": step.display_name, "duration_s": elapsed}})

        state.metadata["agent_timings"] = agent_timings
        state.metadata["trace_id"] = TraceContext.get().get("trace_id")
        state.metadata["pipeline_checkpoints"] = len(checkpoints)
        return state

    def _attach_structured_report(self, state: AgentState) -> None:
        """Attach frontend-friendly structured report metadata after the full pipeline."""
        sections_data = {
            "executive_summary": state.analysis_report or state.action_report or "",
            "technical_analysis": str(state.metadata.get("technical_summary", "")),
            "macro_context": str(state.metadata.get("macro_context", "")),
            "debate_summary": str(state.metadata.get("debate_summary", "")),
            "strategy_recommendations": str(
                state.metadata.get("strategy_recommendations", state.action_report or "")
            ),
            "risk_assessment": str(state.metadata.get("risk_assessment", "")),
            "position_context": str(state.metadata.get("position_context", "")),
        }
        state.metadata["structured_report"] = build_structured_report(sections_data, FULL_ANALYSIS)

    async def analyze_symbols(self, symbols: list[str]) -> list[AgentState]:
        """Run analysis pipeline for multiple symbols with concurrency control."""
        logger.info(f"Starting batch analysis for {len(symbols)} symbols: {symbols}")

        max_concurrent = self._config_dict.get("max_concurrent_agents", 4)
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _throttled(symbol: str) -> AgentState:
            async with semaphore:
                return await self.analyze_symbol(symbol)

        tasks = [_throttled(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        states: list[AgentState] = []
        for symbol, result in zip(symbols, results, strict=False):
            if isinstance(result, Exception):
                logger.error(f"Analysis failed for {symbol}: {result}")
                error_state = AgentState(
                    symbol=symbol,
                    trade_date=date.today(),
                    action_report=f"Pipeline Error: {str(result)}",
                )
                error_state.total_steps = len(self._build_pipeline_steps())
                states.append(error_state)
            else:
                states.append(result)  # type: ignore[arg-type]

        logger.info(f"Batch analysis completed: {len(states)} results")
        return states

    async def generate_final_report(self, state: AgentState) -> str:
        """Generate final analysis report using LLM."""
        basic_report = self._generate_basic_report(state)

        try:
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
Analysis Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S %Z')}
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
        health: dict[str, bool] = {}
        legacy_names = {
            "Data-Harvester": "data_harvester",
            "Quant-Brain": "quant_brain",
            "Strategy-Execution": "strategy_exec",
            "Aegis-Memory": "aegis_memory",
        }
        for agent_name, agent in self._agents.items():
            checker = getattr(agent, "health_check", None)
            if callable(checker):
                result = checker()
                is_healthy = bool(await result) if asyncio.iscoroutine(result) else bool(result)
            else:
                is_healthy = agent.status.value in {"idle", "success"}
            health[legacy_names.get(agent_name, agent_name)] = is_healthy
        return health

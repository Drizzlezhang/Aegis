"""Quant-Brain Agent implementation."""

from typing import Dict, List, Any, Optional
import logging

from src.agents.base import BaseAgent
from src.models import AgentState
from src.config import get_config
from src.skills import get_global_registry

from .core import calculate_volume_profile, calculate_gex_walls, calculate_pe_band_valuation, create_support_resistance_levels
from .llm_integration import generate_llm_enhanced_report


logger = logging.getLogger(__name__)


class QuantBrainAgent(BaseAgent):
    """Quant-Brain Agent: Institutional-level quantitative analysis."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            name="Quant-Brain",
            description="Institutional-level quantitative analysis including support/resistance levels and valuation ranges",
            config=config or {}
        )
        self._config = get_config()
        self._skill_registry = get_global_registry()
        self._volume_profile_skill = None
        self._gex_calculator_skill = None

    async def initialize(self) -> None:
        """Initialize quantitative analysis skills."""
        await super().initialize()

        # Load volume profile skill
        try:
            self._volume_profile_skill = self._skill_registry.get_skill("volume_profile")
            if self._volume_profile_skill:
                await self._volume_profile_skill.initialize()
                logger.info("Volume profile skill loaded successfully")
            else:
                logger.warning("Volume profile skill not found in registry")
        except Exception as e:
            logger.error(f"Failed to initialize volume profile skill: {e}")

        # Load GEX calculator skill
        try:
            self._gex_calculator_skill = self._skill_registry.get_skill("gex_calculator")
            if self._gex_calculator_skill:
                await self._gex_calculator_skill.initialize()
                logger.info("GEX calculator skill loaded successfully")
            else:
                logger.warning("GEX calculator skill not found in registry")
        except Exception as e:
            logger.error(f"Failed to initialize GEX calculator skill: {e}")

    async def run(self, state: AgentState) -> AgentState:
        """Execute quantitative analysis for the given symbol."""
        symbol = state.symbol.upper()
        logger.info(f"Quant-Brain starting analysis for symbol: {symbol}")

        # Get data from state
        ohlcv_data = state.ohlcv_data
        options_chain = state.options_chain
        fundamentals = {}  # Placeholder for now

        # Calculate volume profile
        volume_profile = None
        if ohlcv_data:
            volume_profile = await calculate_volume_profile(ohlcv_data, self._volume_profile_skill, self._config)
            if volume_profile:
                state.volume_profile = volume_profile

        # Calculate GEX walls
        gex_walls = None
        if options_chain:
            gex_walls = await calculate_gex_walls(options_chain, self._gex_calculator_skill, self._config)
            if gex_walls:
                state.gex_walls = gex_walls

        # Calculate support/resistance levels
        support_levels, resistance_levels = create_support_resistance_levels(volume_profile, gex_walls)
        state.support_levels = support_levels
        state.resistance_levels = resistance_levels

        # Calculate valuation range
        current_price = options_chain.spot_price if options_chain else None
        if current_price:
            valuation_range = await calculate_pe_band_valuation(
                symbol, current_price, fundamentals, self._config.algorithm.pe_band_percentiles
            )
            if valuation_range:
                state.valuation_range = valuation_range

        # Generate enhanced LLM report
        try:
            enhanced_report = await generate_llm_enhanced_report(
                symbol=state.symbol,
                ohlcv_data=state.ohlcv_data,
                options_chain=state.options_chain,
                support_levels=state.support_levels,
                resistance_levels=state.resistance_levels,
                volume_profile=state.volume_profile,
                gex_walls=state.gex_walls,
                valuation_range=state.valuation_range
            )
            state.analysis_report = enhanced_report
            logger.info(f"Generated enhanced LLM report for {symbol}")
        except Exception as e:
            logger.warning(f"LLM report generation failed: {e}, using basic report")
            # Keep existing basic report

        # Add agent step
        state.add_agent_step(self.name)

        logger.info(f"Quant-Brain completed analysis for symbol: {symbol}")
        return state

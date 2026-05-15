"""Quant-Brain Agent implementation."""

import logging
from typing import Any

from src.agents.base import BaseAgent
from src.config import get_config
from src.models import AgentState
from src.skills import get_global_registry

from .core import (
    calculate_gex_walls,
    calculate_pe_band_valuation,
    calculate_volume_profile,
    create_support_resistance_levels,
)
from .llm_integration import generate_llm_enhanced_report
from .macro_regime import MacroRegimeAnalyzer
from .market_context import analyze_market_context

logger = logging.getLogger(__name__)


class QuantBrainAgent(BaseAgent):
    """Quant-Brain Agent: Institutional-level quantitative analysis."""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(
            name="Quant-Brain",
            description="Institutional-level quantitative analysis including support/resistance levels and valuation ranges",
            config=config or {}
        )
        self._config = get_config()
        self._skill_registry = get_global_registry()
        self._volume_profile_skill: Any = None
        self._gex_calculator_skill: Any = None

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
        fundamentals: dict[str, Any] = {}  # Placeholder for now

        # Analyze market context from market indices
        market_context = analyze_market_context(state.market_indices)
        if market_context.vix_level is not None:
            logger.info(
                f"Market context for {symbol}: VIX={market_context.vix_level:.2f}, "
                f"sentiment={market_context.market_sentiment}, regime={market_context.volatility_regime}"
            )

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

        # Calculate support/resistance levels with market context adjustment
        support_levels, resistance_levels = create_support_resistance_levels(
            volume_profile, gex_walls, market_context=market_context
        )
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

        # Run technical scoring step
        await self._run_technical_score(state)

        # Run macro regime step
        await self._run_macro_regime(state)

        # Generate enhanced LLM report with market context
        try:
            enhanced_report = await generate_llm_enhanced_report(
                symbol=state.symbol,
                ohlcv_data=state.ohlcv_data,
                options_chain=state.options_chain,
                support_levels=state.support_levels,
                resistance_levels=state.resistance_levels,
                volume_profile=state.volume_profile,
                gex_walls=state.gex_walls,
                valuation_range=state.valuation_range,
                market_context=market_context,
            )
            state.analysis_report = enhanced_report
            logger.info(f"Generated enhanced LLM report for {symbol}")
        except Exception as e:
            logger.warning(f"LLM report generation failed: {e}, using basic report")
            # Keep existing basic report

        state.quant_result = state.snapshot_quant()
        state.add_agent_step(self.name)

        logger.info(f"Quant-Brain completed analysis for symbol: {symbol}")
        return state

    async def _run_technical_score(self, state: AgentState) -> None:
        """Calculate 100-point technical score and append to analysis report."""
        try:
            scorer = self._skill_registry.get_skill("technical_scorer")
            if scorer is None:
                logger.warning("Technical scorer skill not found, skipping scoring step")
                return

            current_price = state.options_chain.spot_price if state.options_chain else None
            if current_price is None and state.ohlcv_data:
                current_price = state.ohlcv_data[-1].close

            if current_price is None:
                logger.warning("No current price available, skipping scoring step")
                return

            result = await scorer.execute({
                "ohlcv_data": state.ohlcv_data or [],
                "technical_indicators": self._build_technical_indicators(state),
                "support_levels": [s.price for s in state.support_levels],
                "current_price": current_price,
            })

            if result.success:
                score = result.data
                state.add_agent_step("technical_score")
                breakdown_str = (
                    f"Trend: {score.trend_score:.0f}/30 | "
                    f"Deviation: {score.deviation_score:.0f}/20 | "
                    f"Volume: {score.volume_score:.0f}/15 | "
                    f"Support: {score.support_score:.0f}/10 | "
                    f"MACD: {score.macd_score:.0f}/15 | "
                    f"RSI: {score.rsi_score:.0f}/10"
                )
                state.analysis_report = (
                    state.analysis_report
                    + f"\n## Technical Score\n"
                    f"Grade: {score.grade}, Total: {score.total:.1f}/100\n"
                    f"{breakdown_str}\n"
                )
                logger.info(f"Technical score: Grade={score.grade}, Total={score.total:.1f}")
            else:
                logger.warning(f"Technical scorer failed: {result.error}")
        except Exception as e:
            logger.warning(f"Technical scoring step failed: {e}")

    async def _run_macro_regime(self, state: AgentState) -> None:
        """Analyze macro regime and append to analysis report."""
        try:
            analyzer = MacroRegimeAnalyzer()
            market_data = self._build_market_data(state)
            regime = await analyzer.analyze(market_data)

            state.add_agent_step("macro_regime")
            state.analysis_report = (
                state.analysis_report
                + f"\n## Macro Regime\n"
                f"Regime: {regime.regime} (confidence: {regime.confidence:.2f})\n"
                f"VIX: {regime.vix_signal} | Trend: {regime.market_trend} | "
                f"Sector: {regime.sector_rotation} | "
                f"Safe Haven Pressure: {regime.safe_haven_pressure:.2f} | "
                f"Credit: {regime.credit_spread}\n"
                f"Factors: {regime.factors}\n"
            )
            logger.info(f"Macro regime: {regime.regime} (confidence: {regime.confidence:.2f})")
        except Exception as e:
            logger.warning(f"Macro regime analysis failed: {e}")

    def _build_technical_indicators(self, state: AgentState) -> dict:
        """从 OHLCV 数据中计算基础技术指标。"""
        if not state.ohlcv_data or len(state.ohlcv_data) < 20:
            return {}

        closes = [bar.close for bar in state.ohlcv_data]
        volumes = [bar.volume for bar in state.ohlcv_data]

        indicators: dict[str, Any] = {
            "close": closes[-1],
        }

        if len(closes) >= 50:
            indicators["sma50"] = sum(closes[-50:]) / 50
        if len(closes) >= 200:
            indicators["sma200"] = sum(closes[-200:]) / 200

        if len(closes) >= 15:
            indicators["rsi"] = self._calculate_rsi(closes, period=14)

        if len(closes) >= 35:
            macd, signal, histogram = self._calculate_macd(closes)
            indicators["macd"] = macd
            indicators["macd_signal"] = signal
            if len(closes) >= 5:
                indicators["macd_histogram_expanding"] = closes[-1] > closes[-2] > closes[-3]

        if len(volumes) >= 20:
            avg_vol = sum(volumes[-20:]) / 20
            indicators["relative_volume"] = volumes[-1] / avg_vol if avg_vol > 0 else 0

        if len(closes) >= 20:
            indicators["adx"] = self._estimate_adx(closes, period=14)

        if len(closes) >= 10 and len(volumes) >= 10:
            price_up = closes[-1] > closes[-5]
            vol_up = sum(volumes[-5:]) > sum(volumes[-10:-5])
            indicators["obv_aligned"] = (price_up and vol_up) or (not price_up and not vol_up)

        return indicators

    @staticmethod
    def _calculate_rsi(closes: list[float], period: int = 14) -> float:
        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        recent = deltas[-period:]
        gains = [d for d in recent if d > 0]
        losses = [-d for d in recent if d < 0]
        avg_gain = sum(gains) / period if gains else 0
        avg_loss = sum(losses) / period if losses else 0
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _calculate_macd(closes: list[float]) -> tuple[float, float, float]:
        def ema_recent(data: list[float], period: int) -> float:
            multiplier = 2 / (period + 1)
            result = data[0]
            for price in data[1:]:
                result = (price - result) * multiplier + result
            return result

        ema12 = ema_recent(closes[-26:], 12)
        ema26 = ema_recent(closes[-26:], 26)
        macd_line = ema12 - ema26
        signal = macd_line
        histogram = macd_line - signal
        return macd_line, signal, histogram

    @staticmethod
    def _estimate_adx(closes: list[float], period: int = 14) -> float:
        if len(closes) < period + 1:
            return 0.0
        recent = closes[-period:]
        price_range = max(recent) - min(recent)
        avg_price = sum(recent) / len(recent)
        if avg_price == 0:
            return 0.0
        volatility_pct = (price_range / avg_price) * 100
        return min(volatility_pct * 3, 50)

    def _build_market_data(self, state: AgentState) -> dict[str, Any]:
        """Extract market data from state for regime analysis."""
        market_data: dict[str, Any] = {}

        for idx in state.market_indices:
            symbol = idx.symbol.upper()
            if symbol in ("^VIX", "VIX"):
                market_data["VIX"] = idx.price
            elif symbol in ("SPY", "^GSPC", "SPX"):
                market_data["SPY_trend"] = (
                    "bullish" if idx.change_percent > 0 else "bearish" if idx.change_percent < 0 else "neutral"
                )
            elif symbol in ("QQQ", "^IXIC", "NDX"):
                market_data["QQQ_trend"] = (
                    "bullish" if idx.change_percent > 0 else "bearish" if idx.change_percent < 0 else "neutral"
                )

        return market_data

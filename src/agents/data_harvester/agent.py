"""Data-Harvester Agent implementation."""

import asyncio
import logging
from typing import Any

from src.agents.base import BaseAgent
from src.config import get_config
from src.models import AgentState
from src.skills import get_global_registry

logger = logging.getLogger(__name__)


class DataHarvesterAgent(BaseAgent):
    """Data-Harvester Agent: Collects market data from various sources."""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(
            name="Data-Harvester",
            description="Collects OHLCV data, options chain, and fundamental data from various sources",
            config=config or {}
        )
        self._config = get_config()
        self._skill_registry = get_global_registry()
        self._yfinance_skill: Any = None

    async def initialize(self) -> None:
        """Initialize data sources and skills."""
        await super().initialize()

        # Load yfinance skill
        try:
            self._yfinance_skill = self._skill_registry.get_skill("yfinance_ohlcv")
            if self._yfinance_skill:
                await self._yfinance_skill.initialize()
                logger.info("yfinance skill loaded successfully")
            else:
                logger.warning("yfinance skill not found in registry")
        except Exception as e:
            logger.error(f"Failed to initialize yfinance skill: {e}")

    async def _get_ohlcv_data(self, symbol: str) -> list[Any] | None:
        """Get OHLCV data for a symbol."""
        if not self._yfinance_skill:
            logger.error("yfinance skill not available")
            return None

        try:
            result = await self._yfinance_skill.execute({
                "symbol": symbol,
                "data_type": "ohlcv",
                "period": self._config.data_source.cache_ttl_seconds > 300 and "90d" or "60d",
                "interval": "1d"
            })

            if result.success:
                return result.data  # type: ignore[no-any-return]
            else:
                logger.error(f"Failed to get OHLCV for {symbol}: {result.error}")
                return None
        except Exception as e:
            logger.error(f"Error getting OHLCV for {symbol}: {e}")
            return None

    async def _get_options_chain(self, symbol: str) -> Any | None:
        """Get options chain for a symbol."""
        if not self._yfinance_skill:
            logger.error("yfinance skill not available")
            return None

        try:
            result = await self._yfinance_skill.execute({
                "symbol": symbol,
                "data_type": "options"
            })

            if result.success:
                return result.data
            else:
                logger.error(f"Failed to get options chain for {symbol}: {result.error}")
                return None
        except Exception as e:
            logger.error(f"Error getting options chain for {symbol}: {e}")
            return None

    async def _get_fundamentals(self, symbol: str) -> dict[str, Any] | None:
        """Get fundamental data for a symbol."""
        if not self._yfinance_skill:
            logger.error("yfinance skill not available")
            return None

        try:
            result = await self._yfinance_skill.execute({
                "symbol": symbol,
                "data_type": "fundamentals"
            })

            if result.success:
                return result.data  # type: ignore[no-any-return]
            else:
                logger.warning(f"Failed to get fundamentals for {symbol}: {result.error}")
                return None
        except Exception as e:
            logger.warning(f"Error getting fundamentals for {symbol}: {e}")
            return None

    async def _get_all_data(self, symbol: str) -> dict[str, Any]:
        """Get all data types in parallel."""
        tasks = [
            self._get_ohlcv_data(symbol),
            self._get_options_chain(symbol),
            self._get_fundamentals(symbol)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        data: dict[str, Any] = {}
        data_types = ["ohlcv", "options", "fundamentals"]

        for i, result in enumerate(results):
            data_type = data_types[i]
            if isinstance(result, Exception):
                logger.error(f"Error getting {data_type} for {symbol}: {result}")
                data[data_type] = None
            else:
                data[data_type] = result

        return data

    async def run(self, state: AgentState) -> AgentState:
        """Execute data harvesting for the given symbol."""
        symbol = state.symbol.upper()
        logger.info(f"Data-Harvester starting for symbol: {symbol}")

        # Get all data
        data = await self._get_all_data(symbol)

        # Update state with data
        if data["ohlcv"]:
            state.ohlcv_data = data["ohlcv"]
        if data["options"]:
            state.options_chain = data["options"]

        # Add agent step
        state.add_agent_step(self.name)

        logger.info(f"Data-Harvester completed for symbol: {symbol}")
        return state

    def _create_analysis_report(self, symbol: str, data: dict[str, Any]) -> str:
        """Create a brief analysis report of the collected data."""
        report = f"Data-Harvester Report for {symbol}\n"
        report += "=" * 40 + "\n"

        # OHLCV summary
        if data.get("ohlcv"):
            ohlcv_list = data["ohlcv"]
            if ohlcv_list:
                latest = ohlcv_list[-1]
                report += f"OHLCV: {latest.timestamp.date()} Close={latest.close:.2f}, Volume={latest.volume:,}\n"
            else:
                report += "OHLCV: No data available\n"
        else:
            report += "OHLCV: Failed to retrieve\n"

        # Options summary
        if data.get("options"):
            options = data["options"]
            report += f"Options: {len(options.calls)} calls, {len(options.puts)} puts\n"
            report += f"Spot Price: {options.spot_price:.2f}\n"
            if options.expiry_dates:
                nearest = options.get_nearest_expiry()
                if nearest:
                    report += f"Nearest Expiry: {nearest}\n"
        else:
            report += "Options: Failed to retrieve\n"

        # Fundamentals summary
        if data.get("fundamentals"):
            fundamentals = data["fundamentals"]
            if fundamentals.get("pe_ratio"):
                report += f"P/E Ratio: {fundamentals['pe_ratio']:.2f}\n"
            if fundamentals.get("market_cap"):
                market_cap = fundamentals['market_cap']
                if market_cap >= 1e9:
                    report += f"Market Cap: ${market_cap/1e9:.2f}B\n"
                else:
                    report += f"Market Cap: ${market_cap/1e6:.2f}M\n"
        else:
            report += "Fundamentals: Not available\n"

        report += "=" * 40
        return report

    async def health_check(self) -> bool:
        """Check if data sources are healthy."""
        if not self._yfinance_skill:
            return False

        try:
            # Try to get data for a test symbol (QQQ)
            result = await self._yfinance_skill.execute({
                "symbol": "QQQ",
                "data_type": "ohlcv",
                "period": "1d",
                "interval": "1d"
            })
            return result.success  # type: ignore[no-any-return]
        except Exception:
            return False

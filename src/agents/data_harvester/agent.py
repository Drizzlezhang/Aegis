"""Data-Harvester Agent implementation."""

import logging
from typing import Any

from src.agents.base import BaseAgent
from src.agents.data_harvester.base_fetcher import FetcherStatus
from src.agents.data_harvester.data_normalizer import DataNormalizer
from src.agents.data_harvester.fetcher_manager import DataFetcherManager
from src.agents.data_harvester.fetchers.yfinance_fetcher import YFinanceFetcher
from src.config import get_config
from src.models import AgentState, MarketIndex
from src.skills import get_global_registry

logger = logging.getLogger(__name__)


class DataHarvesterAgent(BaseAgent):
    """Data-Harvester Agent: Collects market data from various sources with automatic fallback."""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(
            name="Data-Harvester",
            description="Collects OHLCV data, options chain, and fundamental data from various sources",
            config=config or {}
        )
        self._config = get_config()
        self._skill_registry = get_global_registry()
        self._data_source_priority: list[str] = []
        self._skills: dict[str, Any] = {}
        self._yfinance_skill: Any | None = None
        self._fetcher_manager: DataFetcherManager | None = None

    async def initialize(self) -> None:
        """Initialize data sources and skills."""
        await super().initialize()

        # Build priority list based on config
        ds_config = self._config.data_source
        priority = []

        if ds_config.yfinance_enabled:
            priority.append("yfinance_ohlcv")
        if ds_config.alpha_vantage_enabled:
            priority.append("alpha_vantage_ohlcv")
        if ds_config.longbridge_enabled:
            priority.append("longbridge_ohlcv")
        if ds_config.futu_enabled:
            priority.append("futu_ohlcv")
        if ds_config.tiger_enabled:
            priority.append("tiger_ohlcv")

        self._data_source_priority = priority or ["yfinance_ohlcv"]

        # Load all skills in priority order
        yfinance_skill: Any | None = None
        for skill_name in self._data_source_priority:
            try:
                skill = self._skill_registry.get_skill(skill_name)
                if skill:
                    await skill.initialize()
                    self._skills[skill_name] = skill
                    if skill_name == "yfinance_ohlcv":
                        yfinance_skill = skill
                        self._yfinance_skill = skill
                    logger.info(f"{skill_name} skill loaded successfully")
                else:
                    logger.warning(f"{skill_name} skill not found in registry")
            except Exception as e:
                logger.error(f"Failed to initialize {skill_name} skill: {e}")

        if not self._skills:
            logger.error("No data source skills available!")

        # Build fetcher manager with available fetchers
        fetchers: list[Any] = []
        if ds_config.yfinance_enabled:
            fetchers.append(YFinanceFetcher(skill=yfinance_skill))

        if fetchers:
            self._fetcher_manager = DataFetcherManager(fetchers, ds_config)
            logger.info(f"DataFetcherManager initialized with {len(fetchers)} fetchers")

    def _get_skill(self, name: str) -> Any | None:
        """Get a loaded skill by name."""
        return self._skills.get(name)

    async def _try_skill(
        self,
        skill_name: str,
        symbol: str,
        data_type: str,
        extra_params: dict[str, Any] | None = None
    ) -> Any | None:
        """Try to execute a single skill."""
        skill = self._get_skill(skill_name)
        if not skill:
            return None

        params: dict[str, Any] = {"symbol": symbol, "data_type": data_type}
        if extra_params:
            params.update(extra_params)

        try:
            result = await skill.execute(params)
            if result.success:
                return result.data  # type: ignore[no-any-return]
            logger.warning(f"{skill_name} failed for {symbol} ({data_type}): {result.error}")
        except Exception as e:
            logger.warning(f"{skill_name} error for {symbol} ({data_type}): {e}")

        return None

    async def _get_ohlcv_data(self, symbol: str) -> list[Any] | None:
        """Get OHLCV data with automatic fallback across data sources."""
        extra = {
            "period": "90d" if self._config.data_source.cache_ttl_seconds > 300 else "60d",
            "interval": "1d",
        }

        for skill_name in self._data_source_priority:
            data = await self._try_skill(skill_name, symbol, "ohlcv", extra)
            if data is not None:
                logger.info(f"OHLCV for {symbol} from {skill_name}")
                return data

        logger.error(f"All data sources failed for OHLCV: {symbol}")
        return None

    async def _get_options_chain(self, symbol: str) -> Any | None:
        """Get options chain (yfinance only, alpha_vantage free tier doesn't support)."""
        if "yfinance_ohlcv" in self._skills:
            data = await self._try_skill("yfinance_ohlcv", symbol, "options")
            if data is not None:
                return data

        logger.warning(f"Options chain not available for {symbol} (yfinance required)")
        return None

    async def _get_fundamentals(self, symbol: str) -> dict[str, Any] | None:
        """Get fundamental data with automatic fallback."""
        for skill_name in self._data_source_priority:
            data = await self._try_skill(skill_name, symbol, "fundamentals")
            if data is not None:
                logger.info(f"Fundamentals for {symbol} from {skill_name}")
                return data

        logger.warning(f"All data sources failed for fundamentals: {symbol}")
        return None

    async def _get_market_indices(self) -> list[dict[str, Any]] | None:
        """Get market index snapshots (SPX, NDX, VIX, HSI)."""
        if "yfinance_ohlcv" not in self._skills:
            logger.warning("Market indices require yfinance")
            return None

        try:
            result = await self._try_skill(
                "yfinance_ohlcv", "", "market_indices"
            )
            if result is not None:
                logger.info(f"Market indices retrieved: {len(result)} indices")
                return result
        except Exception as e:
            logger.warning(f"Failed to get market indices: {e}")

        return None

    async def _get_all_data(self, symbol: str) -> dict[str, Any]:
        """Get all data types with fallback."""
        ohlcv = await self._get_ohlcv_data(symbol)
        options = await self._get_options_chain(symbol)
        fundamentals = await self._get_fundamentals(symbol)
        market_indices = await self._get_market_indices()

        return {
            "ohlcv": ohlcv,
            "options": options,
            "fundamentals": fundamentals,
            "market_indices": market_indices,
        }

    async def run(self, state: AgentState) -> AgentState:
        """Execute data harvesting for the given symbol."""
        symbol = state.symbol.upper()
        logger.info(f"Data-Harvester starting for symbol: {symbol}")

        # Primary path: use DataFetcherManager
        if self._fetcher_manager is not None:
            try:
                raw_data = await self._fetcher_manager.fetch_all(symbol)

                # Normalize OHLCV
                ohlcv = DataNormalizer.normalize_ohlcv(raw_data.get("ohlcv", {}), symbol)
                if ohlcv:
                    state.ohlcv_data = ohlcv

                # Normalize options chain
                options = DataNormalizer.normalize_options_chain(raw_data.get("options_chain"), symbol)
                if options:
                    state.options_chain = options

                # Market indices via skill (not in manager)
                market_indices = await self._get_market_indices()
                if market_indices:
                    indices: list[MarketIndex] = []
                    for idx in market_indices:
                        try:
                            indices.append(MarketIndex(**idx))
                        except Exception:
                            logger.debug(f"Skipping invalid market index data: {idx}")
                    state.market_indices = indices

                state.add_agent_step(self.name)
                logger.info(f"Data-Harvester completed for symbol: {symbol} (via DataFetcherManager)")
                return state

            except Exception as e:
                logger.warning(f"DataFetcherManager failed, falling back to SkillRegistry: {e}")

        # Fallback path: use SkillRegistry
        data = await self._get_all_data(symbol)

        if data["ohlcv"]:
            state.ohlcv_data = data["ohlcv"]
        if data["options"]:
            state.options_chain = data["options"]
        if data["market_indices"]:
            indices: list[MarketIndex] = []
            for idx in data["market_indices"]:
                try:
                    indices.append(MarketIndex(**idx))
                except Exception:
                    logger.debug(f"Skipping invalid market index data: {idx}")
            state.market_indices = indices

        state.add_agent_step(self.name)
        logger.info(f"Data-Harvester completed for symbol: {symbol} (via SkillRegistry fallback)")
        return state

    async def health_check(self) -> bool:
        """Check if at least one data source is healthy."""
        if self._fetcher_manager is not None:
            try:
                report = await self._fetcher_manager.health_report()
                for _name, health in report.items():
                    if health.status in (FetcherStatus.HEALTHY, FetcherStatus.DEGRADED):
                        return True
                return False
            except Exception:
                pass

        # Fallback to skill-based health check
        if not self._skills:
            return False

        for _skill_name, skill in self._skills.items():
            try:
                result = await skill.execute({
                    "symbol": "QQQ",
                    "data_type": "ohlcv",
                    "period": "1d",
                    "interval": "1d",
                })
                if result.success:
                    return True
            except Exception:
                continue

        return False

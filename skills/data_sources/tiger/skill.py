"""Tiger Trade (老虎证券) data source skill.

This skill provides access to US, Hong Kong, and A-share market data
via the Tiger Trade OpenAPI.

Setup:
1. Register at https://www.itiger.com/ and apply for OpenAPI
2. Generate account_id and private_key
3. Set environment variables:
   TIGER_ACCOUNT_ID=your_account_id
   TIGER_PRIVATE_KEY=your_private_key

For best results, install the official SDK:
   pip install tigeropen

This skill is primarily for US/HK markets.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any

import cachetools
import requests

from src.skills.base import BaseSkill, SkillResult, SkillType

logger = logging.getLogger(__name__)

# Optional: tigeropen SDK
try:
    from tigeropen.tiger_open_client import TigerOpenClient
    from tigeropen.common.const import Market, BarPeriod
    from tigeropen.quote.quote_client import QuoteClient

    TIGER_SDK_AVAILABLE = True
except ImportError:
    TIGER_SDK_AVAILABLE = False
    TigerOpenClient = None  # type: ignore[misc,assignment]
    Market = None  # type: ignore[misc,assignment]
    BarPeriod = None  # type: ignore[misc,assignment]
    QuoteClient = None  # type: ignore[misc,assignment]
    logger.warning(
        "tigeropen not installed. Using HTTP fallback (limited functionality). "
        "Install with: pip install tigeropen"
    )

API_BASE = "https://openapi.itiger.com/gateway"


class TigerSkill(BaseSkill):
    """Tiger Trade data source skill for US/HK/A-share markets."""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._account_id = os.environ.get("TIGER_ACCOUNT_ID", "")
        self._private_key = os.environ.get("TIGER_PRIVATE_KEY", "")

        self.cache_ttl = config.get("cache_ttl", 300) if config else 300
        self.max_retries = config.get("max_retries", 3) if config else 3
        self.retry_delay = config.get("retry_delay", 1) if config else 1
        self.market = config.get("market", "US") if config else "US"

        self._cache = cachetools.TTLCache(maxsize=100, ttl=self.cache_ttl)
        self._quote_client: Any = None

    @property
    def skill_type(self) -> SkillType:
        return SkillType.DATA_SOURCE

    @property
    def description(self) -> str:
        return "Tiger Trade (老虎证券) US/HK/A-share OHLCV data source"

    @property
    def version(self) -> str:
        return "0.1.0"

    def get_required_params(self) -> list[str]:
        return ["symbol"]

    async def initialize(self) -> None:
        """Initialize Tiger connection."""
        if TIGER_SDK_AVAILABLE and self._account_id and self._private_key:
            client_config = TigerOpenClient(
                tiger_id=self._account_id,
                private_key=self._private_key,
            )
            self._quote_client = QuoteClient(client_config)
            logger.info("Tiger Trade client initialized")
        elif not TIGER_SDK_AVAILABLE:
            logger.warning("Tiger SDK not available. Using HTTP fallback mode.")
        await super().initialize()

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol for Tiger API.

        Tiger uses format like:
        - US: AAPL
        - HK: 00700
        - CN: 600519
        Market is specified separately in API calls.
        """
        return symbol.upper().strip()

    def _get_tiger_market(self) -> Any:
        """Get Tiger Market enum from config."""
        if not TIGER_SDK_AVAILABLE:
            return None

        mapping = {
            "US": Market.US,
            "HK": Market.HK,
            "CN": Market.CN,
        }
        return mapping.get(self.market, Market.US)

    def _get_bar_period(self, interval: str) -> Any:
        """Convert interval to Tiger BarPeriod."""
        if not TIGER_SDK_AVAILABLE:
            return None

        mapping = {
            "1m": BarPeriod.ONE_MINUTE,
            "5m": BarPeriod.FIVE_MINUTES,
            "15m": BarPeriod.FIFTEEN_MINUTES,
            "30m": BarPeriod.THIRTY_MINUTES,
            "60m": BarPeriod.SIXTY_MINUTES,
            "1d": BarPeriod.DAY,
            "1w": BarPeriod.WEEK,
            "1M": BarPeriod.MONTH,
        }
        return mapping.get(interval, BarPeriod.DAY)

    def _get_candlesticks_sdk(
        self, symbol: str, period: int, interval: str
    ) -> list[dict[str, Any]]:
        """Get candlesticks using Tiger SDK."""
        if not self._quote_client:
            raise RuntimeError("Tiger quote client not initialized")

        tiger_symbol = self._normalize_symbol(symbol)
        market = self._get_tiger_market()
        bar_period = self._get_bar_period(interval)

        # Calculate begin time
        end_time = datetime.now()
        if interval in ["1d", "1w", "1M"]:
            begin_time = end_time - timedelta(days=period)
        else:
            # For intraday, limit to recent data
            begin_time = end_time - timedelta(days=7)

        bars = self._quote_client.get_bars(
            symbols=[tiger_symbol],
            period=bar_period,
            begin_time=begin_time.strftime("%Y-%m-%d %H:%M:%S"),
            end_time=end_time.strftime("%Y-%m-%d %H:%M:%S"),
            market=market,
        )

        if bars is None or bars.empty:
            raise ValueError(f"No data returned for {symbol}")

        records = []
        for _, row in bars.iterrows():
            records.append({
                "timestamp": int(row["time"].timestamp()) if hasattr(row["time"], "timestamp") else int(row["time"]),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": int(row["volume"]),
            })

        return records[-period:] if len(records) > period else records

    def _get_candlesticks_http(
        self, symbol: str, period: int, interval: str
    ) -> list[dict[str, Any]]:
        """Fallback: Get candlesticks via HTTP."""
        raise RuntimeError(
            "Tiger HTTP fallback not implemented. "
            "Please install tigeropen: pip install tigeropen"
        )

    def _get_candlesticks(self, symbol: str, period: int, interval: str) -> list[dict[str, Any]]:
        """Get candlestick data from Tiger."""
        cache_key = f"tiger_{symbol}_{period}_{interval}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if TIGER_SDK_AVAILABLE and self._quote_client:
            candlesticks = self._get_candlesticks_sdk(symbol, period, interval)
        else:
            candlesticks = self._get_candlesticks_http(symbol, period, interval)

        if not candlesticks:
            raise ValueError(f"No candlestick data for {symbol}")

        self._cache[cache_key] = candlesticks
        return candlesticks

    def _candles_to_ohlcv(self, candlesticks: list[dict[str, Any]], symbol: str) -> list[Any]:
        """Convert Tiger candlesticks to OHLCV objects."""
        import pandas as pd

        records = []
        for candle in candlesticks:
            ts = candle.get("timestamp", 0)
            if isinstance(ts, (int, float)):
                dt = datetime.fromtimestamp(ts)
            else:
                dt = pd.to_datetime(ts)

            records.append({
                "date": dt,
                "Open": float(candle.get("open", 0)),
                "High": float(candle.get("high", 0)),
                "Low": float(candle.get("low", 0)),
                "Close": float(candle.get("close", 0)),
                "Volume": int(candle.get("volume", 0)),
            })

        df = pd.DataFrame(records)
        df = df.sort_values("date").reset_index(drop=True)

        from src.models import OHLCV
        return OHLCV.from_dataframe(df, symbol)

    async def get_ohlcv(self, symbol: str, period: str = "60d", interval: str = "1d") -> list[Any]:
        """Get OHLCV data for a symbol."""
        import asyncio

        try:
            days = int(period.replace("d", "").replace("mo", "").replace("y", ""))
            if "mo" in period:
                days *= 30
            elif "y" in period:
                days *= 365

            candlesticks = await asyncio.to_thread(self._get_candlesticks, symbol, days, interval)
            return self._candles_to_ohlcv(candlesticks, symbol)
        except Exception as e:
            logger.error(f"Failed to get OHLCV for {symbol} from Tiger: {e}")
            raise

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        """Get real-time quote for a symbol."""
        import asyncio

        cache_key = f"quote_{symbol}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            tiger_symbol = self._normalize_symbol(symbol)

            if TIGER_SDK_AVAILABLE and self._quote_client:
                market = self._get_tiger_market()
                quotes = self._quote_client.get_quote(symbols=[tiger_symbol], market=market)

                if quotes is None or quotes.empty:
                    raise ValueError(f"No quote data for {symbol}")

                row = quotes.iloc[0]
                quote = {
                    "symbol": symbol,
                    "last_price": float(row.get("latest_price", 0)),
                    "open": float(row.get("open", 0)),
                    "high": float(row.get("high", 0)),
                    "low": float(row.get("low", 0)),
                    "volume": int(row.get("volume", 0)),
                    "turnover": float(row.get("turnover", 0)),
                    "timestamp": int(datetime.now().timestamp()),
                }
            else:
                raise RuntimeError(
                    "Tiger SDK not available for quote. "
                    "Install with: pip install tigeropen"
                )

            self._cache[cache_key] = quote
            return quote
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            return {}

    async def execute(self, params: dict[str, Any]) -> SkillResult:
        """Execute the skill."""
        try:
            symbol = params.get("symbol", "").upper()
            data_type = params.get("data_type", "ohlcv")

            if not symbol:
                return SkillResult.error_result("Symbol is required")

            if not self._account_id or not self._private_key:
                return SkillResult.error_result(
                    "Tiger credentials not configured. "
                    "Set TIGER_ACCOUNT_ID and TIGER_PRIVATE_KEY"
                )

            if data_type == "ohlcv":
                period = params.get("period", "60d")
                interval = params.get("interval", "1d")
                ohlcv_data = await self.get_ohlcv(symbol, period, interval)
                return SkillResult.success_result(
                    ohlcv_data,
                    {"symbol": symbol, "data_type": "ohlcv", "source": "tiger"},
                )

            elif data_type == "quote":
                quote = await self.get_quote(symbol)
                return SkillResult.success_result(
                    quote,
                    {"symbol": symbol, "data_type": "quote", "source": "tiger"},
                )

            else:
                return SkillResult.error_result(f"Unknown data_type: {data_type}")

        except Exception as e:
            logger.error(f"Tiger skill execution failed: {e}")
            return SkillResult.error_result(str(e))

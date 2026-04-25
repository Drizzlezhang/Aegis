"""Futu (富途) data source skill.

This skill provides access to Hong Kong, A-share, and US market data
via the FutuNiuNiu OpenD service.

Setup:
1. Install FutuNiuNiu client and login
2. Enable OpenD service (usually runs on 127.0.0.1:11111)
3. Set environment variables:
   FUTU_OPEND_ADDRESS=127.0.0.1
   FUTU_OPEND_PORT=11111

For best results, install the official SDK:
   pip install futu-api

This skill is primarily for HK/A-share markets.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any

import cachetools
import requests

from src.skills.base import BaseSkill, SkillResult, SkillType

logger = logging.getLogger(__name__)

# Optional: futu-api SDK
try:
    from futu import OpenQuoteContext, KLType, SubType, RET_OK

    FUTU_SDK_AVAILABLE = True
except ImportError:
    FUTU_SDK_AVAILABLE = False
    OpenQuoteContext = None  # type: ignore[misc,assignment]
    KLType = None  # type: ignore[misc,assignment]
    SubType = None  # type: ignore[misc,assignment]
    RET_OK = 0  # type: ignore[misc]
    logger.warning(
        "futu-api not installed. Using HTTP fallback (limited functionality). "
        "Install with: pip install futu-api"
    )


class FutuSkill(BaseSkill):
    """Futu data source skill for HK/A-share/US markets."""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._opend_address = os.environ.get("FUTU_OPEND_ADDRESS", "127.0.0.1")
        self._opend_port = int(os.environ.get("FUTU_OPEND_PORT", "11111"))

        self.cache_ttl = config.get("cache_ttl", 300) if config else 300
        self.max_retries = config.get("max_retries", 3) if config else 3
        self.retry_delay = config.get("retry_delay", 1) if config else 1
        self.market = config.get("market", "HK") if config else "HK"

        self._cache = cachetools.TTLCache(maxsize=100, ttl=self.cache_ttl)
        self._quote_ctx: Any = None

    @property
    def skill_type(self) -> SkillType:
        return SkillType.DATA_SOURCE

    @property
    def description(self) -> str:
        return "Futu (富途) HK/A-share/US OHLCV data source"

    @property
    def version(self) -> str:
        return "0.1.0"

    def get_required_params(self) -> list[str]:
        return ["symbol"]

    async def initialize(self) -> None:
        """Initialize Futu connection."""
        if FUTU_SDK_AVAILABLE and not self._quote_ctx:
            self._quote_ctx = OpenQuoteContext(
                host=self._opend_address,
                port=self._opend_port,
            )
            logger.info(f"Futu OpenD connected: {self._opend_address}:{self._opend_port}")
        elif not FUTU_SDK_AVAILABLE:
            logger.warning("Futu SDK not available. Using HTTP fallback mode.")
        await super().initialize()

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol for Futu API.

        Futu uses format like:
        - HK: 00700.HK (Tencent)
        - US: AAPL.US
        - SH: 600519.SH
        - SZ: 000001.SZ
        """
        symbol = symbol.upper().strip()

        # If already contains market suffix, return as-is
        if "." in symbol:
            return symbol

        # Append market suffix based on config
        return f"{symbol}.{self.market}"

    def _get_kl_type(self, interval: str) -> Any:
        """Convert interval string to Futu KLType."""
        if not FUTU_SDK_AVAILABLE:
            return None

        mapping = {
            "1m": KLType.K_1M,
            "5m": KLType.K_5M,
            "15m": KLType.K_15M,
            "30m": KLType.K_30M,
            "60m": KLType.K_60M,
            "1d": KLType.K_DAY,
            "1w": KLType.K_WEEK,
            "1M": KLType.K_MON,
        }
        return mapping.get(interval, KLType.K_DAY)

    def _get_candlesticks_sdk(
        self, symbol: str, period: int, interval: str
    ) -> list[dict[str, Any]]:
        """Get candlesticks using Futu SDK."""
        if not self._quote_ctx:
            raise RuntimeError("Futu quote context not initialized")

        futu_symbol = self._normalize_symbol(symbol)
        kl_type = self._get_kl_type(interval)

        ret, data, page_req_key = self._quote_ctx.request_history_kl(
            code=futu_symbol,
            ktype=kl_type,
            autype=0,  # No adjustment
            max_count=period,
        )

        if ret != RET_OK:
            raise RuntimeError(f"Futu API error: {data}")

        # Convert DataFrame to list of dicts
        records = []
        for _, row in data.iterrows():
            records.append({
                "timestamp": int(row["time_key"].timestamp()),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": int(row["volume"]),
            })

        return records

    def _get_candlesticks_http(
        self, symbol: str, period: int, interval: str
    ) -> list[dict[str, Any]]:
        """Fallback: Get candlesticks via HTTP (requires custom endpoint)."""
        raise RuntimeError(
            "Futu HTTP fallback not implemented. "
            "Please install futu-api: pip install futu-api"
        )

    def _get_candlesticks(self, symbol: str, period: int, interval: str) -> list[dict[str, Any]]:
        """Get candlestick data from Futu."""
        cache_key = f"futu_{symbol}_{period}_{interval}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if FUTU_SDK_AVAILABLE and self._quote_ctx:
            candlesticks = self._get_candlesticks_sdk(symbol, period, interval)
        else:
            candlesticks = self._get_candlesticks_http(symbol, period, interval)

        if not candlesticks:
            raise ValueError(f"No candlestick data for {symbol}")

        self._cache[cache_key] = candlesticks
        return candlesticks

    def _candles_to_ohlcv(self, candlesticks: list[dict[str, Any]], symbol: str) -> list[Any]:
        """Convert Futu candlesticks to OHLCV objects."""
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
            logger.error(f"Failed to get OHLCV for {symbol} from Futu: {e}")
            raise

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        """Get real-time quote for a symbol."""
        import asyncio

        cache_key = f"quote_{symbol}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            futu_symbol = self._normalize_symbol(symbol)

            if FUTU_SDK_AVAILABLE and self._quote_ctx:
                ret, data = self._quote_ctx.get_market_snapshot([futu_symbol])
                if ret != RET_OK:
                    raise RuntimeError(f"Futu quote error: {data}")

                row = data.iloc[0]
                quote = {
                    "symbol": symbol,
                    "last_price": float(row.get("last_price", 0)),
                    "open": float(row.get("open_price", 0)),
                    "high": float(row.get("high_price", 0)),
                    "low": float(row.get("low_price", 0)),
                    "volume": int(row.get("volume", 0)),
                    "turnover": float(row.get("turnover", 0)),
                    "timestamp": int(datetime.now().timestamp()),
                }
            else:
                raise RuntimeError(
                    "Futu SDK not available for quote. "
                    "Install with: pip install futu-api"
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

            if not self._opend_address:
                return SkillResult.error_result(
                    "Futu OpenD not configured. "
                    "Set FUTU_OPEND_ADDRESS and FUTU_OPEND_PORT"
                )

            if data_type == "ohlcv":
                period = params.get("period", "60d")
                interval = params.get("interval", "1d")
                ohlcv_data = await self.get_ohlcv(symbol, period, interval)
                return SkillResult.success_result(
                    ohlcv_data,
                    {"symbol": symbol, "data_type": "ohlcv", "source": "futu"},
                )

            elif data_type == "quote":
                quote = await self.get_quote(symbol)
                return SkillResult.success_result(
                    quote,
                    {"symbol": symbol, "data_type": "quote", "source": "futu"},
                )

            else:
                return SkillResult.error_result(f"Unknown data_type: {data_type}")

        except Exception as e:
            logger.error(f"Futu skill execution failed: {e}")
            return SkillResult.error_result(str(e))

    async def cleanup(self) -> None:
        """Clean up Futu connection."""
        if self._quote_ctx:
            self._quote_ctx.close()
            self._quote_ctx = None
            logger.info("Futu connection closed")

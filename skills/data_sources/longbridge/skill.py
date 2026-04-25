"""Longbridge (长桥) data source skill.

This skill provides access to Hong Kong and A-share market data
via the Longbridge OpenAPI.

Setup:
1. Register at https://open.longbridgeapp.com/
2. Create an app to get AppKey and AppSecret
3. Generate an access token
4. Set environment variables:
   LONGBRIDGE_APP_KEY=your_app_key
   LONGBRIDGE_APP_SECRET=your_app_secret
   LONGBRIDGE_ACCESS_TOKEN=your_access_token

For US stocks, prefer yfinance or alpha_vantage.
This skill is primarily for HK/A-share markets.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any

import cachetools
import requests

from src.models import OHLCV
from src.skills.base import BaseSkill, SkillResult, SkillType

logger = logging.getLogger(__name__)

API_BASE = "https://openapi.longbridgeapp.com"


class LongbridgeSkill(BaseSkill):
    """Longbridge data source skill for HK/A-share markets."""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._app_key = os.environ.get("LONGBRIDGE_APP_KEY", "")
        self._app_secret = os.environ.get("LONGBRIDGE_APP_SECRET", "")
        self._access_token = os.environ.get("LONGBRIDGE_ACCESS_TOKEN", "")

        self.cache_ttl = config.get("cache_ttl", 300) if config else 300
        self.max_retries = config.get("max_retries", 3) if config else 3
        self.retry_delay = config.get("retry_delay", 1) if config else 1
        self.market = config.get("market", "HK") if config else "HK"

        self._cache = cachetools.TTLCache(maxsize=100, ttl=self.cache_ttl)

    @property
    def skill_type(self) -> SkillType:
        return SkillType.DATA_SOURCE

    @property
    def description(self) -> str:
        return "Longbridge (长桥) HK/A-share OHLCV data source"

    @property
    def version(self) -> str:
        return "0.1.0"

    def get_required_params(self) -> list[str]:
        return ["symbol"]

    def _headers(self) -> dict[str, str]:
        """Build authentication headers."""
        return {
            "X-Api-Key": self._app_key,
            "X-Api-Secret": self._app_secret,
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    def _request(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make authenticated request to Longbridge API."""
        url = f"{API_BASE}{endpoint}"

        for attempt in range(self.max_retries):
            try:
                resp = requests.get(url, headers=self._headers(), params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()

                if data.get("code") != 0:
                    msg = data.get("message", "Unknown error")
                    logger.warning(f"Longbridge API error: {msg}")
                    if attempt < self.max_retries - 1:
                        import time
                        time.sleep(self.retry_delay * (attempt + 1))
                        continue
                    raise RuntimeError(f"Longbridge API error: {msg}")

                return data.get("data", {})

            except requests.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise
                logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                import time
                time.sleep(self.retry_delay * (attempt + 1))

        return {}

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol for Longbridge API.

        Longbridge uses format like:
        - HK: 00700.HK (Tencent)
        - US: AAPL.US
        - CN: 600519.SH
        """
        symbol = symbol.upper().strip()

        # If already contains market suffix, return as-is
        if "." in symbol:
            return symbol

        # Append market suffix based on config
        return f"{symbol}.{self.market}"

    def _get_candlesticks(self, symbol: str, period: int, interval: str) -> list[dict[str, Any]]:
        """Get candlestick data from Longbridge."""
        cache_key = f"lb_{symbol}_{period}_{interval}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        lb_symbol = self._normalize_symbol(symbol)

        # Longbridge candlestick endpoint
        # Reference: https://open.longbridgeapp.com/docs/quote/pull/candlestick
        data = self._request(
            "/v1/quote/candlesticks",
            {
                "symbol": lb_symbol,
                "period": interval,  # 1d, 1w, 1M
                "count": period,
                "adjust_type": "0",  # No adjustment
            },
        )

        candlesticks = data.get("candlesticks", [])
        if not candlesticks:
            raise ValueError(f"No candlestick data for {symbol}")

        self._cache[cache_key] = candlesticks
        return candlesticks

    def _candles_to_ohlcv(self, candlesticks: list[dict[str, Any]], symbol: str) -> list[OHLCV]:
        """Convert Longbridge candlesticks to OHLCV objects."""
        import pandas as pd

        records = []
        for candle in candlesticks:
            # Longbridge returns timestamps in seconds
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
        df = df.rename(columns={"date": "date"})

        return OHLCV.from_dataframe(df, symbol)

    async def get_ohlcv(self, symbol: str, period: str = "60d", interval: str = "1d") -> list[OHLCV]:
        """Get OHLCV data for a symbol."""
        import asyncio

        try:
            # Convert period to count
            days = int(period.replace("d", "").replace("mo", "").replace("y", ""))
            if "mo" in period:
                days *= 30
            elif "y" in period:
                days *= 365

            candlesticks = await asyncio.to_thread(self._get_candlesticks, symbol, days, interval)
            return self._candles_to_ohlcv(candlesticks, symbol)
        except Exception as e:
            logger.error(f"Failed to get OHLCV for {symbol} from Longbridge: {e}")
            raise

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        """Get real-time quote for a symbol."""
        import asyncio

        cache_key = f"quote_{symbol}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            lb_symbol = self._normalize_symbol(symbol)
            data = await asyncio.to_thread(
                self._request,
                "/v1/quote/realtime",
                {"symbol": lb_symbol},
            )

            quote = {
                "symbol": symbol,
                "last_price": data.get("last_done"),
                "open": data.get("open"),
                "high": data.get("high"),
                "low": data.get("low"),
                "volume": data.get("volume"),
                "turnover": data.get("turnover"),
                "timestamp": data.get("timestamp"),
            }

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

            if not self._app_key or not self._access_token:
                return SkillResult.error_result(
                    "Longbridge credentials not configured. "
                    "Set LONGBRIDGE_APP_KEY, LONGBRIDGE_APP_SECRET, LONGBRIDGE_ACCESS_TOKEN"
                )

            if data_type == "ohlcv":
                period = params.get("period", "60d")
                interval = params.get("interval", "1d")
                ohlcv_data = await self.get_ohlcv(symbol, period, interval)
                return SkillResult.success_result(
                    ohlcv_data,
                    {"symbol": symbol, "data_type": "ohlcv", "source": "longbridge"},
                )

            elif data_type == "quote":
                quote = await self.get_quote(symbol)
                return SkillResult.success_result(
                    quote,
                    {"symbol": symbol, "data_type": "quote", "source": "longbridge"},
                )

            else:
                return SkillResult.error_result(f"Unknown data_type: {data_type}")

        except Exception as e:
            logger.error(f"Longbridge skill execution failed: {e}")
            return SkillResult.error_result(str(e))

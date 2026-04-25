"""Alpha Vantage data source skill."""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any

import cachetools
import pandas as pd
import requests

from src.models import OHLCV
from src.skills.base import BaseSkill, SkillResult, SkillType

logger = logging.getLogger(__name__)

API_BASE = "https://www.alphavantage.co/query"


class AlphaVantageSkill(BaseSkill):
    """Alpha Vantage data source skill (fallback for Yahoo Finance)."""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._api_key = os.environ.get("ALPHA_VANTAGE_API_KEY", "")
        self.cache_ttl = config.get("cache_ttl", 300) if config else 300
        self.max_retries = config.get("max_retries", 3) if config else 3
        self.retry_delay = config.get("retry_delay", 1) if config else 1
        self.rate_limit_calls = config.get("rate_limit_calls", 5) if config else 5
        self.rate_limit_period = config.get("rate_limit_period", 60) if config else 60

        self._cache = cachetools.TTLCache(maxsize=100, ttl=self.cache_ttl)
        self._call_times: list[float] = []

    @property
    def skill_type(self) -> SkillType:
        return SkillType.DATA_SOURCE

    @property
    def description(self) -> str:
        return "Alpha Vantage OHLCV and fundamentals data source"

    @property
    def version(self) -> str:
        return "0.1.0"

    def get_required_params(self) -> list[str]:
        return ["symbol"]

    def _rate_limit(self) -> None:
        """Enforce rate limiting (free tier: 5 calls/minute)."""
        now = time.time()
        # Remove calls outside the rate limit window
        cutoff = now - self.rate_limit_period
        self._call_times = [t for t in self._call_times if t > cutoff]

        if len(self._call_times) >= self.rate_limit_calls:
            sleep_time = self._call_times[0] + self.rate_limit_period - now
            if sleep_time > 0:
                logger.warning(f"Rate limit hit, sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)

        self._call_times.append(time.time())

    def _request(self, params: dict[str, str]) -> dict[str, Any]:
        """Make a rate-limited request to Alpha Vantage API."""
        self._rate_limit()
        params["apikey"] = self._api_key

        for attempt in range(self.max_retries):
            try:
                resp = requests.get(API_BASE, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()

                # Check for API errors / rate limit messages
                if "Information" in data or "Note" in data:
                    msg = data.get("Information") or data.get("Note", "")
                    logger.warning(f"Alpha Vantage API message: {msg}")
                    if "rate limit" in msg.lower() or "call frequency" in msg.lower():
                        if attempt < self.max_retries - 1:
                            wait = self.rate_limit_period / self.rate_limit_calls
                            logger.info(f"Rate limited, waiting {wait:.1f}s before retry")
                            time.sleep(wait)
                            continue
                        raise RuntimeError(f"Alpha Vantage rate limit exceeded: {msg}")

                return data
            except requests.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise
                logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                time.sleep(self.retry_delay * (attempt + 1))

        return {}

    def _get_daily_data(self, symbol: str) -> pd.DataFrame:
        """Get daily OHLCV data."""
        cache_key = f"daily_{symbol}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        data = self._request({
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": "full",
        })

        ts_key = "Time Series (Daily)"
        if ts_key not in data:
            raise ValueError(f"No daily data for {symbol}: {data}")

        records = []
        for date_str, values in data[ts_key].items():
            records.append({
                "Date": date_str,
                "Open": float(values["1. open"]),
                "High": float(values["2. high"]),
                "Low": float(values["3. low"]),
                "Close": float(values["4. close"]),
                "Volume": int(values["5. volume"]),
            })

        df = pd.DataFrame(records)
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date").reset_index(drop=True)

        self._cache[cache_key] = df
        return df

    async def get_ohlcv(self, symbol: str, period: str = "60d", interval: str = "1d") -> list[OHLCV]:
        """Get OHLCV data for a symbol."""
        try:
            data = await asyncio.to_thread(self._get_daily_data, symbol)

            # Filter by period
            days = int(period.replace("d", "").replace("mo", "").replace("y", ""))
            if "mo" in period:
                days *= 30
            elif "y" in period:
                days *= 365

            cutoff = datetime.now() - timedelta(days=days)
            data = data[data["Date"] >= cutoff]

            if data.empty:
                raise ValueError(f"No data for {symbol} in period {period}")

            # Rename columns to match OHLCV expectations
            data = data.rename(columns={"Date": "date"})

            return OHLCV.from_dataframe(data, symbol)
        except Exception as e:
            logger.error(f"Failed to get OHLCV for {symbol} from Alpha Vantage: {e}")
            raise

    async def get_fundamentals(self, symbol: str) -> dict[str, Any]:
        """Get fundamental data for a symbol."""
        cache_key = f"fundamentals_{symbol}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            data = await asyncio.to_thread(
                self._request,
                {"function": "OVERVIEW", "symbol": symbol}
            )

            if not data or "Symbol" not in data:
                logger.warning(f"No fundamentals for {symbol}")
                return {}

            fundamentals = {
                "pe_ratio": data.get("PERatio"),
                "forward_pe": data.get("ForwardPE"),
                "peg_ratio": data.get("PEGRatio"),
                "eps": data.get("EPS"),
                "forward_eps": None,
                "dividend_yield": data.get("DividendYield"),
                "market_cap": data.get("MarketCapitalization"),
                "enterprise_value": None,
                "ev_to_ebitda": data.get("EVToEBITDA"),
                "profit_margins": data.get("ProfitMargin"),
                "operating_margins": data.get("OperatingMarginTTM"),
                "return_on_equity": data.get("ReturnOnEquityTTM"),
                "return_on_assets": data.get("ReturnOnAssetsTTM"),
                "debt_to_equity": data.get("DebtToEquityRatio"),
                "current_ratio": data.get("CurrentRatio"),
                "quick_ratio": data.get("QuickRatio"),
                "beta": data.get("Beta"),
                "52_week_high": data.get("52WeekHigh"),
                "52_week_low": data.get("52WeekLow"),
                "average_volume": data.get("AverageVolume"),
                "volume": None,
            }

            # Clean None and NA values
            fundamentals = {
                k: v for k, v in fundamentals.items()
                if v is not None and v != "None" and v != ""
            }

            # Convert numeric strings
            for key in ["pe_ratio", "forward_pe", "peg_ratio", "eps", "beta",
                        "profit_margins", "operating_margins", "return_on_equity",
                        "return_on_assets", "debt_to_equity", "current_ratio",
                        "quick_ratio", "dividend_yield"]:
                if key in fundamentals:
                    try:
                        fundamentals[key] = float(fundamentals[key])
                    except (ValueError, TypeError):
                        pass

            self._cache[cache_key] = fundamentals
            return fundamentals

        except Exception as e:
            logger.error(f"Failed to get fundamentals for {symbol}: {e}")
            return {}

    async def execute(self, params: dict[str, Any]) -> SkillResult:
        """Execute the skill."""
        try:
            symbol = params.get("symbol", "").upper()
            data_type = params.get("data_type", "ohlcv")

            if not symbol:
                return SkillResult.error_result("Symbol is required")

            if not self._api_key:
                return SkillResult.error_result("ALPHA_VANTAGE_API_KEY not configured")

            if data_type == "ohlcv":
                period = params.get("period", "60d")
                ohlcv_data = await self.get_ohlcv(symbol, period)
                return SkillResult.success_result(
                    ohlcv_data,
                    {"symbol": symbol, "data_type": "ohlcv", "source": "alpha_vantage"}
                )

            elif data_type == "fundamentals":
                fundamentals = await self.get_fundamentals(symbol)
                return SkillResult.success_result(
                    fundamentals,
                    {"symbol": symbol, "data_type": "fundamentals", "source": "alpha_vantage"}
                )

            elif data_type == "all":
                ohlcv_data = await self.get_ohlcv(symbol)
                fundamentals = await self.get_fundamentals(symbol)
                return SkillResult.success_result(
                    {"ohlcv": ohlcv_data, "fundamentals": fundamentals},
                    {"symbol": symbol, "data_type": "all", "source": "alpha_vantage"}
                )

            else:
                return SkillResult.error_result(f"Unknown data_type: {data_type}")

        except Exception as e:
            logger.error(f"Alpha Vantage skill execution failed: {e}")
            return SkillResult.error_result(str(e))

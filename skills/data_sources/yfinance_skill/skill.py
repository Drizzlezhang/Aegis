"""Yahoo Finance data source skill."""

import asyncio
import logging
from datetime import datetime
from typing import Any

import cachetools
import pandas as pd
import yfinance as yf

from src.models import OHLCV, OptionChain, OptionContract, OptionType
from src.skills.base import BaseSkill, SkillResult, SkillType

logger = logging.getLogger(__name__)


class YFinanceSkill(BaseSkill):
    """Yahoo Finance data source skill."""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.cache_ttl = config.get("cache_ttl", 300) if config else 300
        self.max_retries = config.get("max_retries", 3) if config else 3
        self.retry_delay = config.get("retry_delay", 1) if config else 1

        # Create cache
        self._cache = cachetools.TTLCache(maxsize=100, ttl=self.cache_ttl)
        self._ticker_cache: dict[str, yf.Ticker] = {}

    @property
    def skill_type(self) -> SkillType:
        return SkillType.DATA_SOURCE

    @property
    def description(self) -> str:
        return "Yahoo Finance OHLCV and options chain data source"

    @property
    def version(self) -> str:
        return "0.1.0"

    def get_required_params(self) -> list[str]:
        return ["symbol"]

    def _get_ticker(self, symbol: str) -> yf.Ticker:
        """Get or create yfinance Ticker object."""
        if symbol not in self._ticker_cache:
            self._ticker_cache[symbol] = yf.Ticker(symbol)
        return self._ticker_cache[symbol]

    def _get_ohlcv_data(
        self,
        symbol: str,
        period: str | None = None,
        interval: str = "1d",
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame:
        """Get OHLCV data with caching."""
        cache_key = f"ohlcv_{symbol}_{period or ''}_{interval}_{start or ''}_{end or ''}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        ticker = self._get_ticker(symbol)

        for attempt in range(self.max_retries):
            try:
                if start and end:
                    data = ticker.history(start=start, end=end, interval=interval)
                elif period:
                    data = ticker.history(period=period, interval=interval)
                else:
                    raise ValueError("Either period or start/end must be provided")

                if data.empty:
                    raise ValueError(f"No data for symbol {symbol}")

                self._cache[cache_key] = data
                return data
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                logger.warning(f"Attempt {attempt + 1} failed for {symbol}: {e}")
                asyncio.sleep(self.retry_delay)

    async def get_ohlcv(
        self,
        symbol: str,
        period: str | None = "60d",
        interval: str = "1d",
        start: str | None = None,
        end: str | None = None,
    ) -> list[OHLCV]:
        """Get OHLCV data for a symbol."""
        try:
            data = await asyncio.to_thread(
                self._get_ohlcv_data, symbol, period, interval, start, end
            )

            # Reset index to make date a column
            data = data.reset_index()

            # Convert to OHLCV objects
            ohlcv_list = OHLCV.from_dataframe(data, symbol)
            return ohlcv_list
        except Exception as e:
            logger.error(f"Failed to get OHLCV for {symbol}: {e}")
            raise

    async def get_options_chain(self, symbol: str) -> OptionChain:
        """Get options chain for a symbol."""
        cache_key = f"options_{symbol}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        ticker = self._get_ticker(symbol)

        try:
            # Get spot price
            spot_data = await asyncio.to_thread(
                self._get_ohlcv_data, symbol, "1d", "1d"
            )
            spot_price = float(spot_data.iloc[-1]["Close"]) if not spot_data.empty else 0.0

            # Get options chain
            options_dates = ticker.options
            if not options_dates:
                raise ValueError(f"No options data for symbol {symbol}")

            # Convert string dates to date objects
            expiry_dates = []
            for date_str in options_dates:
                try:
                    expiry_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    expiry_dates.append(expiry_date)
                except ValueError:
                    continue

            # Select expiry dates: nearest for short-term, leaps for long-term
            from datetime import date as date_cls
            today = date_cls.today()

            # Find nearest expiry (for short-term strategies)
            nearest_expiry = min(expiry_dates) if expiry_dates else None

            # Find a LEAPS expiry (>= 300 days) for long-term strategies
            leaps_expiry = None
            for exp in sorted(expiry_dates):
                if (exp - today).days >= 300:
                    leaps_expiry = exp
                    break

            calls: list[OptionContract] = []
            puts: list[OptionContract] = []

            def _process_chain(options_chain, expiry_date):
                for _, row in options_chain.calls.iterrows():
                    contract = OptionContract(
                        symbol=symbol,
                        underlying=symbol,
                        contract_symbol=row.get("contractSymbol", ""),
                        strike=float(row.get("strike", 0)),
                        expiry=expiry_date,
                        option_type=OptionType.CALL,
                        last_price=float(row.get("lastPrice", 0)) if pd.notna(row.get("lastPrice")) else None,
                        bid=float(row.get("bid", 0)) if pd.notna(row.get("bid")) else None,
                        ask=float(row.get("ask", 0)) if pd.notna(row.get("ask")) else None,
                        volume=int(row.get("volume", 0)) if pd.notna(row.get("volume")) else None,
                        open_interest=int(row.get("openInterest", 0)) if pd.notna(row.get("openInterest")) else None,
                        implied_volatility=float(row.get("impliedVolatility", 0)) if pd.notna(row.get("impliedVolatility")) else None,
                    )
                    calls.append(contract)
                for _, row in options_chain.puts.iterrows():
                    contract = OptionContract(
                        symbol=symbol,
                        underlying=symbol,
                        contract_symbol=row.get("contractSymbol", ""),
                        strike=float(row.get("strike", 0)),
                        expiry=expiry_date,
                        option_type=OptionType.PUT,
                        last_price=float(row.get("lastPrice", 0)) if pd.notna(row.get("lastPrice")) else None,
                        bid=float(row.get("bid", 0)) if pd.notna(row.get("bid")) else None,
                        ask=float(row.get("ask", 0)) if pd.notna(row.get("ask")) else None,
                        volume=int(row.get("volume", 0)) if pd.notna(row.get("volume")) else None,
                        open_interest=int(row.get("openInterest", 0)) if pd.notna(row.get("openInterest")) else None,
                        implied_volatility=float(row.get("impliedVolatility", 0)) if pd.notna(row.get("impliedVolatility")) else None,
                    )
                    puts.append(contract)

            # Fetch nearest expiry
            if nearest_expiry:
                expiry_str = nearest_expiry.strftime("%Y-%m-%d")
                options_chain = ticker.option_chain(expiry_str)
                _process_chain(options_chain, nearest_expiry)

            # Fetch LEAPS expiry if different from nearest
            if leaps_expiry and leaps_expiry != nearest_expiry:
                leaps_str = leaps_expiry.strftime("%Y-%m-%d")
                leaps_chain = ticker.option_chain(leaps_str)
                _process_chain(leaps_chain, leaps_expiry)

            # Create OptionChain
            chain = OptionChain(
                symbol=symbol,
                timestamp=datetime.now(),
                spot_price=spot_price,
                calls=calls,
                puts=puts,
                expiry_dates=expiry_dates
            )

            self._cache[cache_key] = chain
            return chain

        except Exception as e:
            logger.error(f"Failed to get options chain for {symbol}: {e}")
            raise

    async def get_market_indices(self, indices: list[dict[str, str]] | None = None) -> list[dict[str, Any]]:
        """Get market index snapshots (SPX, NDX, VIX, HSI, etc.)."""
        if indices is None:
            indices = [
                {"symbol": "^GSPC", "name": "S&P 500", "market": "US"},
                {"symbol": "^IXIC", "name": "Nasdaq 100", "market": "US"},
                {"symbol": "^DJI", "name": "Dow Jones", "market": "US"},
                {"symbol": "^VIX", "name": "VIX", "market": "US"},
                {"symbol": "^HSI", "name": "Hang Seng", "market": "HK"},
            ]

        results = []
        for idx in indices:
            sym = idx["symbol"]
            cache_key = f"index_{sym}"
            if cache_key in self._cache:
                results.append(self._cache[cache_key])
                continue

            try:
                ticker = self._get_ticker(sym)
                hist = await asyncio.to_thread(ticker.history, period="1d", interval="1d")
                info = await asyncio.to_thread(lambda: ticker.info)

                if hist.empty:
                    continue

                latest = hist.iloc[-1]
                prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
                price = float(latest["Close"])
                prev = float(prev_close) if prev_close else price
                change = price - prev
                change_pct = (change / prev * 100) if prev else 0.0

                result = {
                    "symbol": sym,
                    "name": idx["name"],
                    "price": round(price, 2),
                    "change": round(change, 2),
                    "change_percent": round(change_pct, 2),
                    "timestamp": datetime.now(),
                    "market": idx.get("market", ""),
                }
                self._cache[cache_key] = result
                results.append(result)
            except Exception as e:
                logger.warning(f"Failed to get index {sym}: {e}")
                continue

        return results

    async def get_fundamentals(self, symbol: str) -> dict[str, Any]:
        """Get fundamental data for a symbol."""
        cache_key = f"fundamentals_{symbol}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        ticker = self._get_ticker(symbol)

        try:
            info = ticker.info
            fundamentals = {
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "peg_ratio": info.get("pegRatio"),
                "eps": info.get("trailingEps"),
                "forward_eps": info.get("forwardEps"),
                "dividend_yield": info.get("dividendYield"),
                "market_cap": info.get("marketCap"),
                "enterprise_value": info.get("enterpriseValue"),
                "ev_to_ebitda": info.get("enterpriseToEbitda"),
                "profit_margins": info.get("profitMargins"),
                "operating_margins": info.get("operatingMargins"),
                "return_on_equity": info.get("returnOnEquity"),
                "return_on_assets": info.get("returnOnAssets"),
                "debt_to_equity": info.get("debtToEquity"),
                "current_ratio": info.get("currentRatio"),
                "quick_ratio": info.get("quickRatio"),
                "beta": info.get("beta"),
                "52_week_high": info.get("fiftyTwoWeekHigh"),
                "52_week_low": info.get("fiftyTwoWeekLow"),
                "average_volume": info.get("averageVolume"),
                "volume": info.get("volume"),
            }

            # Clean None values
            fundamentals = {k: v for k, v in fundamentals.items() if v is not None}

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

            if data_type == "ohlcv":
                period = params.get("period", "60d")
                interval = params.get("interval", "1d")
                ohlcv_data = await self.get_ohlcv(symbol, period, interval)
                return SkillResult.success_result(ohlcv_data, {"symbol": symbol, "data_type": "ohlcv"})

            elif data_type == "options":
                options_chain = await self.get_options_chain(symbol)
                return SkillResult.success_result(options_chain, {"symbol": symbol, "data_type": "options"})

            elif data_type == "fundamentals":
                fundamentals = await self.get_fundamentals(symbol)
                return SkillResult.success_result(fundamentals, {"symbol": symbol, "data_type": "fundamentals"})

            elif data_type == "market_indices":
                indices = await self.get_market_indices()
                return SkillResult.success_result(
                    indices, {"data_type": "market_indices", "count": len(indices)}
                )

            elif data_type == "all":
                # Get all data types
                ohlcv_task = self.get_ohlcv(symbol)
                options_task = self.get_options_chain(symbol)
                fundamentals_task = self.get_fundamentals(symbol)

                ohlcv_data, options_chain, fundamentals = await asyncio.gather(
                    ohlcv_task, options_task, fundamentals_task,
                    return_exceptions=True
                )

                # Handle exceptions
                if isinstance(ohlcv_data, Exception):
                    logger.error(f"Failed to get OHLCV: {ohlcv_data}")
                    ohlcv_data = []
                if isinstance(options_chain, Exception):
                    logger.error(f"Failed to get options: {options_chain}")
                    options_chain = None
                if isinstance(fundamentals, Exception):
                    logger.error(f"Failed to get fundamentals: {fundamentals}")
                    fundamentals = {}

                result = {
                    "ohlcv": ohlcv_data,
                    "options": options_chain,
                    "fundamentals": fundamentals
                }

                return SkillResult.success_result(result, {"symbol": symbol, "data_type": "all"})

            else:
                return SkillResult.error_result(f"Unknown data_type: {data_type}")

        except Exception as e:
            logger.error(f"Skill execution failed: {e}")
            return SkillResult.error_result(str(e))

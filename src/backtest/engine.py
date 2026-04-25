"""Backtest engine core logic."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from src.models import OHLCV
from src.skills import SkillRegistry


@dataclass
class TradeRecord:
    """A single simulated trade."""

    entry_date: str
    exit_date: str | None = None
    entry_price: float = 0.0
    exit_price: float | None = None
    shares: int = 0
    pnl: float | None = None
    pnl_percent: float | None = None
    status: str = "open"  # "open" | "closed"


@dataclass
class BacktestResult:
    """Complete backtest result."""

    symbol: str
    strategy: str
    equity_curve: list[dict[str, Any]]
    trades: list[TradeRecord]
    metrics: dict[str, float]
    monthly_returns: list[dict[str, float]]


class BacktestEngine:
    """Simple backtest engine based on SMA crossover signals."""

    def __init__(self, short_window: int = 20, long_window: int = 50):
        self.short_window = short_window
        self.long_window = long_window

    async def run_backtest(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        initial_capital: float = 100000.0,
    ) -> BacktestResult:
        """Run a backtest for the given symbol and date range."""
        # Fetch historical data for the date range
        ohlcv_data = await self._fetch_ohlcv(symbol, start_date, end_date)
        if not ohlcv_data:
            raise ValueError(f"No data available for {symbol}")

        # Filter by date range
        ohlcv_data = [
            d for d in ohlcv_data
            if start_date <= d.timestamp.date() <= end_date
        ]

        if len(ohlcv_data) < self.long_window + 5:
            raise ValueError(
                f"Insufficient data for {symbol}: {len(ohlcv_data)} points, "
                f"need at least {self.long_window + 5}"
            )

        # Calculate SMAs
        closes = [d.close for d in ohlcv_data]
        short_sma = self._calculate_sma(closes, self.short_window)
        long_sma = self._calculate_sma(closes, self.long_window)

        # Generate signals and simulate trades
        equity_curve, trades = self._simulate(
            ohlcv_data, short_sma, long_sma, initial_capital
        )

        # Calculate metrics
        from .metrics import calculate_metrics, calculate_monthly_returns

        metrics = calculate_metrics(equity_curve, trades)
        monthly_returns = calculate_monthly_returns(equity_curve)

        return BacktestResult(
            symbol=symbol,
            strategy=f"SMA{self.short_window}/{self.long_window}",
            equity_curve=equity_curve,
            trades=trades,
            metrics=metrics,
            monthly_returns=monthly_returns,
        )

    def _date_range_to_period(self, start_date: date, end_date: date) -> str:
        """Convert date range to yfinance period string."""
        days = (end_date - start_date).days
        if days <= 7:
            return "1mo"
        if days <= 30:
            return "3mo"
        if days <= 90:
            return "6mo"
        if days <= 180:
            return "1y"
        if days <= 365:
            return "2y"
        if days <= 730:
            return "5y"
        return "max"

    async def _fetch_ohlcv(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[OHLCV]:
        """Fetch OHLCV data via yfinance skill using date range."""
        from skills.data_sources.yfinance_skill.skill import YFinanceSkill

        skill = YFinanceSkill()
        await skill.initialize()
        # yfinance end date is exclusive, so add one day
        end_exclusive = end_date + __import__("datetime").timedelta(days=1)
        return await skill.get_ohlcv(
            symbol,
            interval="1d",
            start=start_date.isoformat(),
            end=end_exclusive.isoformat(),
        )

    @staticmethod
    def _calculate_sma(prices: list[float], window: int) -> list[float | None]:
        """Calculate Simple Moving Average."""
        result: list[float | None] = []
        for i in range(len(prices)):
            if i < window - 1:
                result.append(None)
            else:
                result.append(sum(prices[i - window + 1 : i + 1]) / window)
        return result

    def _simulate(
        self,
        ohlcv_data: list[OHLCV],
        short_sma: list[float | None],
        long_sma: list[float | None],
        initial_capital: float,
    ) -> tuple[list[dict[str, Any]], list[TradeRecord]]:
        """Simulate trading based on SMA crossover signals."""
        capital = initial_capital
        shares = 0
        position_open = False
        trades: list[TradeRecord] = []
        current_trade: TradeRecord | None = None

        equity_curve: list[dict[str, Any]] = []

        # Benchmark: buy and hold
        first_price = ohlcv_data[0].close
        benchmark_shares = initial_capital / first_price

        for i, day in enumerate(ohlcv_data):
            price = day.close
            date_str = day.timestamp.strftime("%Y-%m-%d")

            short = short_sma[i]
            long = long_sma[i]

            # Signal detection (need both SMAs ready)
            if short is not None and long is not None and i > 0:
                prev_short = short_sma[i - 1]
                prev_long = long_sma[i - 1]

                if prev_short is not None and prev_long is not None:
                    # Golden cross: short crosses above long -> buy
                    if prev_short <= prev_long and short > long and not position_open:
                        shares = int(capital / price)
                        if shares > 0:
                            cost = shares * price
                            capital -= cost
                            position_open = True
                            current_trade = TradeRecord(
                                entry_date=date_str,
                                entry_price=price,
                                shares=shares,
                                status="open",
                            )

                    # Death cross: short crosses below long -> sell
                    elif prev_short >= prev_long and short < long and position_open:
                        if current_trade:
                            proceeds = shares * price
                            capital += proceeds
                            pnl = proceeds - (current_trade.shares * current_trade.entry_price)
                            pnl_percent = (pnl / (current_trade.shares * current_trade.entry_price)) * 100
                            current_trade.exit_date = date_str
                            current_trade.exit_price = price
                            current_trade.pnl = pnl
                            current_trade.pnl_percent = pnl_percent
                            current_trade.status = "closed"
                            trades.append(current_trade)

                        shares = 0
                        position_open = False
                        current_trade = None

            # Calculate portfolio value
            portfolio_value = capital + shares * price
            benchmark_value = benchmark_shares * price

            equity_curve.append({
                "date": date_str,
                "value": portfolio_value,
                "benchmark": benchmark_value,
            })

        # Close any open position at the end
        if position_open and current_trade:
            last_day = ohlcv_data[-1]
            last_price = last_day.close
            last_date = last_day.timestamp.strftime("%Y-%m-%d")
            proceeds = shares * last_price
            capital += proceeds
            pnl = proceeds - (current_trade.shares * current_trade.entry_price)
            pnl_percent = (pnl / (current_trade.shares * current_trade.entry_price)) * 100
            current_trade.exit_date = last_date
            current_trade.exit_price = last_price
            current_trade.pnl = pnl
            current_trade.pnl_percent = pnl_percent
            current_trade.status = "closed"
            trades.append(current_trade)

            # Update final equity curve point
            equity_curve[-1]["value"] = capital

        return equity_curve, trades

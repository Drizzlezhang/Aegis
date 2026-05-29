"""Options strategy backtesting engine."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from .options_pricing import OptionPosition, OptionType, position_pnl
from .strategies import _calculate_rsi


class OptionsStrategy(StrEnum):
    COVERED_CALL = "covered_call"
    BULL_SPREAD = "bull_spread"
    LEAPS_CALL = "leaps_call"


@dataclass
class OptionsTradeResult:
    entry_date: date
    exit_date: date
    strategy: OptionsStrategy
    entry_spot: float
    exit_spot: float
    legs: list[dict]  # serialized OptionPosition info
    pnl: float
    pnl_pct: float
    max_risk: float
    hold_days: int


@dataclass
class OptionsBacktestResult:
    symbol: str
    strategy: OptionsStrategy
    start_date: date
    end_date: date
    initial_capital: float
    final_capital: float
    trades: list[OptionsTradeResult]
    equity_curve: list[dict]  # [{date, equity}]
    metrics: dict


def _serialize_leg(leg: OptionPosition) -> dict:
    return {
        "option_type": leg.option_type.value,
        "strike": leg.strike,
        "premium": leg.premium,
        "quantity": leg.quantity,
        "dte": leg.dte,
    }


class OptionsBacktestEngine:
    """Backtest engine for options strategies."""

    def __init__(
        self,
        strategy: OptionsStrategy,
        dte_target: int = 45,
        profit_target_pct: float = 50.0,
        stop_loss_pct: float = 200.0,
        roll_dte: int = 21,
        rsi_threshold: float = 40.0,
    ):
        self.strategy = strategy
        self.dte_target = dte_target
        self.profit_target_pct = profit_target_pct
        self.stop_loss_pct = stop_loss_pct
        self.roll_dte = roll_dte
        self.rsi_threshold = rsi_threshold

    async def run(
        self,
        symbol: str,
        price_data: list[dict],
        initial_capital: float = 100_000,
    ) -> OptionsBacktestResult:
        """Run options backtest on historical price data."""
        if not price_data:
            return self._empty_result(symbol, initial_capital)

        closes = [d["close"] for d in price_data]
        if len(closes) < 15:
            return self._empty_result(symbol, initial_capital)

        # Calculate RSI for entry signals
        rsi_values = _calculate_rsi(closes, period=14)

        capital = initial_capital
        position: dict | None = None
        trades: list[OptionsTradeResult] = []
        equity_curve: list[dict] = []

        start_date = _parse_date(price_data[0]["date"])
        end_date = _parse_date(price_data[-1]["date"])

        for i, day in enumerate(price_data):
            spot = day["close"]
            day_date = _parse_date(day["date"])
            rsi = rsi_values[i] if i < len(rsi_values) else None

            current_pnl = 0.0

            if position is None:
                # Check entry signal
                if rsi is not None and rsi < self.rsi_threshold:
                    legs = self._construct_legs(self.strategy, spot, self.dte_target)
                    max_risk = self._compute_max_risk(legs, spot)
                    max_profit = self._compute_max_profit(legs, spot)
                    position = {
                        "legs": legs,
                        "entry_index": i,
                        "entry_spot": spot,
                        "entry_date": day_date,
                        "max_risk": max_risk,
                        "max_profit": max_profit,
                    }
            else:
                dte_remaining = position["legs"][0].dte - (i - position["entry_index"])
                current_pnl = position_pnl(position["legs"], spot, dte_remaining)

                # covered_call: add stock PnL
                if self.strategy == OptionsStrategy.COVERED_CALL:
                    stock_pnl = (spot - position["entry_spot"]) * 100
                    current_pnl += stock_pnl

                # Check exit conditions
                should_exit = False
                if dte_remaining <= 0:
                    should_exit = True
                elif dte_remaining < self.roll_dte:
                    should_exit = True
                elif position["max_profit"] > 0 and current_pnl >= position["max_profit"] * self.profit_target_pct / 100:
                    should_exit = True
                elif position["max_risk"] > 0 and current_pnl <= -position["max_risk"] * self.stop_loss_pct / 100:
                    should_exit = True

                if should_exit:
                    hold_days = i - position["entry_index"]
                    pnl_pct = (current_pnl / position["max_risk"]) * 100 if position["max_risk"] > 0 else 0.0
                    trades.append(OptionsTradeResult(
                        entry_date=position["entry_date"],
                        exit_date=day_date,
                        strategy=self.strategy,
                        entry_spot=position["entry_spot"],
                        exit_spot=spot,
                        legs=[_serialize_leg(leg) for leg in position["legs"]],
                        pnl=current_pnl,
                        pnl_pct=pnl_pct,
                        max_risk=position["max_risk"],
                        hold_days=hold_days,
                    ))
                    capital += current_pnl
                    current_pnl = 0.0
                    position = None

            equity = capital + current_pnl
            equity_curve.append({"date": day["date"], "equity": equity})

        # Force close at end
        if position is not None:
            last_day = price_data[-1]
            last_spot = last_day["close"]
            last_date = _parse_date(last_day["date"])
            dte_remaining = position["legs"][0].dte - (len(price_data) - 1 - position["entry_index"])
            final_pnl = position_pnl(position["legs"], last_spot, dte_remaining)
            if self.strategy == OptionsStrategy.COVERED_CALL:
                final_pnl += (last_spot - position["entry_spot"]) * 100
            hold_days = len(price_data) - 1 - position["entry_index"]
            pnl_pct = (final_pnl / position["max_risk"]) * 100 if position["max_risk"] > 0 else 0.0
            trades.append(OptionsTradeResult(
                entry_date=position["entry_date"],
                exit_date=last_date,
                strategy=self.strategy,
                entry_spot=position["entry_spot"],
                exit_spot=last_spot,
                legs=[_serialize_leg(leg) for leg in position["legs"]],
                pnl=final_pnl,
                pnl_pct=pnl_pct,
                max_risk=position["max_risk"],
                hold_days=hold_days,
            ))
            capital += final_pnl
            equity_curve[-1]["equity"] = capital

        metrics = self._compute_metrics(trades, equity_curve, initial_capital)

        return OptionsBacktestResult(
            symbol=symbol,
            strategy=self.strategy,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            final_capital=capital,
            trades=trades,
            equity_curve=equity_curve,
            metrics=metrics,
        )

    def _construct_legs(self, strategy: OptionsStrategy, spot: float, dte: int) -> list[OptionPosition]:
        """Construct option legs based on strategy type."""
        if strategy == OptionsStrategy.COVERED_CALL:
            call_premium = spot * 0.03
            return [
                OptionPosition(OptionType.CALL, spot * 1.05, call_premium, -1, dte),
            ]
        elif strategy == OptionsStrategy.BULL_SPREAD:
            long_premium = spot * 0.05
            short_premium = spot * 0.02
            return [
                OptionPosition(OptionType.CALL, spot, long_premium, 1, dte),
                OptionPosition(OptionType.CALL, spot * 1.10, short_premium, -1, dte),
            ]
        elif strategy == OptionsStrategy.LEAPS_CALL:
            premium = spot * 0.25
            return [
                OptionPosition(OptionType.CALL, spot * 0.80, premium, 1, dte),
            ]
        return []

    def _compute_max_risk(self, legs: list[OptionPosition], spot: float) -> float:
        """Compute maximum risk for the position."""
        if self.strategy == OptionsStrategy.COVERED_CALL:
            # Stock risk: spot * 100 (if stock goes to zero), offset by premium
            return spot * 100
        elif self.strategy == OptionsStrategy.BULL_SPREAD:
            # Net debit = (long_premium - short_premium) * 100
            net_debit = sum(
                leg.premium * leg.quantity * 100 for leg in legs
            )
            return abs(net_debit) if net_debit > 0 else abs(net_debit)
        elif self.strategy == OptionsStrategy.LEAPS_CALL:
            # Premium paid
            return sum(leg.premium * abs(leg.quantity) * 100 for leg in legs if leg.quantity > 0)
        return 0.0

    def _compute_max_profit(self, legs: list[OptionPosition], spot: float) -> float:
        """Compute maximum profit for the position."""
        if self.strategy == OptionsStrategy.COVERED_CALL:
            # Max profit = premium received (when stock stays flat or rises slightly)
            return sum(abs(leg.premium) * abs(leg.quantity) * 100 for leg in legs if leg.quantity < 0)
        elif self.strategy == OptionsStrategy.BULL_SPREAD:
            # Width of strikes - net debit
            strikes = sorted([leg.strike for leg in legs])
            width = (strikes[-1] - strikes[0]) * 100
            net_debit = sum(leg.premium * leg.quantity * 100 for leg in legs)
            return max(0.0, width - abs(net_debit))
        elif self.strategy == OptionsStrategy.LEAPS_CALL:
            # Theoretically unlimited, use a large estimate
            return spot * 100
        return 0.0

    def _compute_metrics(
        self,
        trades: list[OptionsTradeResult],
        equity_curve: list[dict],
        initial: float,
    ) -> dict:
        """Compute backtest performance metrics."""
        if not equity_curve:
            return _empty_metrics()

        final_equity = equity_curve[-1]["equity"]
        total_return = (final_equity - initial) / initial * 100 if initial > 0 else 0.0

        # Win rate
        closed_trades = trades
        wins = [t for t in closed_trades if t.pnl > 0]
        losses = [t for t in closed_trades if t.pnl <= 0]
        total_trades = len(closed_trades)
        win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0.0

        # Profit factor
        total_win = sum(t.pnl for t in wins)
        total_loss = sum(abs(t.pnl) for t in losses)
        profit_factor = total_win / total_loss if total_loss > 0 else (999.0 if total_win > 0 else 0.0)

        # Max drawdown
        max_drawdown = _calc_max_drawdown(equity_curve)

        # Sharpe ratio
        sharpe = _calc_sharpe(equity_curve)

        # Avg win/loss
        avg_win = total_win / len(wins) if wins else 0.0
        avg_loss = total_loss / len(losses) if losses else 0.0

        # Best/worst trade
        best_trade = max((t.pnl_pct for t in closed_trades), default=0.0)
        worst_trade = min((t.pnl_pct for t in closed_trades), default=0.0)

        # Annualized return
        days = len(equity_curve)
        years = days / 365.0
        if years > 0 and total_return / 100 > -1:
            annualized_return = (((final_equity / initial) ** (1 / years)) - 1) * 100
        else:
            annualized_return = total_return

        return {
            "total_return": total_return,
            "annualized_return": annualized_return,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe,
            "total_trades": float(total_trades),
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "best_trade": best_trade,
            "worst_trade": worst_trade,
        }

    def _empty_result(self, symbol: str, initial_capital: float) -> OptionsBacktestResult:
        return OptionsBacktestResult(
            symbol=symbol,
            strategy=self.strategy,
            start_date=date.today(),
            end_date=date.today(),
            initial_capital=initial_capital,
            final_capital=initial_capital,
            trades=[],
            equity_curve=[],
            metrics=_empty_metrics(),
        )


def _parse_date(date_str: str) -> date:
    """Parse date string to date object."""
    from datetime import datetime
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return date.today()


def _empty_metrics() -> dict:
    return {
        "total_return": 0.0,
        "annualized_return": 0.0,
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "max_drawdown": 0.0,
        "sharpe_ratio": 0.0,
        "total_trades": 0.0,
        "avg_win": 0.0,
        "avg_loss": 0.0,
        "best_trade": 0.0,
        "worst_trade": 0.0,
    }


def _calc_max_drawdown(equity_curve: list[dict]) -> float:
    """Calculate maximum drawdown percentage from equity curve."""
    peak = 0.0
    max_dd = 0.0
    for point in equity_curve:
        value = point["equity"]
        if value > peak:
            peak = value
        if peak > 0:
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
    return max_dd * 100


def _calc_sharpe(equity_curve: list[dict], risk_free_rate: float = 0.02) -> float:
    """Calculate annualized Sharpe ratio."""
    import math
    if len(equity_curve) < 2:
        return 0.0

    daily_returns: list[float] = []
    for i in range(1, len(equity_curve)):
        prev = equity_curve[i - 1]["equity"]
        curr = equity_curve[i]["equity"]
        if prev > 0:
            daily_returns.append((curr - prev) / prev)

    if not daily_returns:
        return 0.0

    avg_return = sum(daily_returns) / len(daily_returns)
    variance = sum((r - avg_return) ** 2 for r in daily_returns) / len(daily_returns)
    std_dev = math.sqrt(variance)

    if std_dev == 0:
        return 0.0

    daily_rf = risk_free_rate / 252
    return ((avg_return - daily_rf) / std_dev) * math.sqrt(252)

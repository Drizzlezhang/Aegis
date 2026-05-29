"""Backtest performance metrics calculation."""

import math
from typing import Any

from src.models.backtest import PerformanceReport

from .engine import TradeRecord


def calculate_metrics(
    equity_curve: list[dict[str, Any]],
    trades: list[TradeRecord],
) -> dict[str, float]:
    """Calculate performance metrics from equity curve and trades.

    Returns:
        Dict with: total_return, annualized_return, win_rate, profit_factor,
        max_drawdown, sharpe_ratio, total_trades, avg_win, avg_loss,
        best_trade, worst_trade
    """
    if not equity_curve:
        return _empty_metrics()

    initial_value = equity_curve[0]["value"]
    final_value = equity_curve[-1]["value"]

    # Total return
    total_return = (final_value - initial_value) / initial_value if initial_value > 0 else 0.0

    # Annualized return
    days = len(equity_curve)
    years = days / 365.0
    annualized_return = (
        math.pow(1 + total_return, 1 / years) - 1 if years > 0 and total_return > -1 else total_return
    )

    # Trade-based metrics
    closed_trades = [t for t in trades if t.status == "closed" and t.pnl is not None]
    total_trades = len(closed_trades)

    wins = [t for t in closed_trades if t.pnl and t.pnl > 0]
    losses = [t for t in closed_trades if t.pnl and t.pnl <= 0]

    win_rate = len(wins) / total_trades if total_trades > 0 else 0.0

    total_win_amount = sum(t.pnl for t in wins if t.pnl is not None)
    total_loss_amount = sum(abs(t.pnl) for t in losses if t.pnl is not None)
    profit_factor = total_win_amount / total_loss_amount if total_loss_amount > 0 else (999.0 if total_win_amount > 0 else 0.0)

    # Max drawdown
    max_drawdown = _calculate_max_drawdown(equity_curve)

    # Sharpe ratio (daily returns, annualized)
    sharpe_ratio = _calculate_sharpe_ratio(equity_curve)

    # Per-trade stats
    avg_win = total_win_amount / len(wins) if wins else 0.0
    avg_loss = total_loss_amount / len(losses) if losses else 0.0
    best_trade = max((t.pnl_percent for t in closed_trades if t.pnl_percent is not None), default=0.0)
    worst_trade = min((t.pnl_percent for t in closed_trades if t.pnl_percent is not None), default=0.0)

    return {
        "total_return": total_return * 100,
        "annualized_return": annualized_return * 100,
        "win_rate": win_rate * 100,
        "profit_factor": profit_factor,
        "max_drawdown": max_drawdown * 100,
        "sharpe_ratio": sharpe_ratio,
        "total_trades": float(total_trades),
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "best_trade": best_trade,
        "worst_trade": worst_trade,
    }


def calculate_performance_report(
    equity_curve: list[dict[str, Any]],
    trades: list[Any],
    risk_free_rate: float = 0.04,
) -> PerformanceReport:
    """Calculate a full PerformanceReport from equity curve and trades."""
    if not equity_curve:
        return PerformanceReport()

    initial_value = equity_curve[0]["value"]
    final_value = equity_curve[-1]["value"]

    total_return = (final_value - initial_value) / initial_value if initial_value > 0 else 0.0
    days = len(equity_curve)
    years = days / 365.0
    annualized_return = (
        math.pow(1 + total_return, 1 / years) - 1 if years > 0 and total_return > -1 else total_return
    )

    closed_trades = [t for t in trades if getattr(t, "status", None) == "closed" and getattr(t, "pnl", None) is not None]
    total_trades = len(closed_trades)
    wins = [t for t in closed_trades if t.pnl and t.pnl > 0]
    losses = [t for t in closed_trades if t.pnl and t.pnl <= 0]

    win_rate = len(wins) / total_trades if total_trades > 0 else 0.0
    total_win = sum(t.pnl for t in wins if t.pnl is not None)
    total_loss = sum(abs(t.pnl) for t in losses if t.pnl is not None)
    profit_factor = total_win / total_loss if total_loss > 0 else (999.0 if total_win > 0 else 0.0)

    max_dd = _calculate_max_drawdown(equity_curve)
    max_dd_duration = calculate_max_drawdown_duration(equity_curve)
    sharpe = _calculate_sharpe_ratio(equity_curve, risk_free_rate)
    sortino = calculate_sortino_ratio(equity_curve, risk_free_rate)
    calmar = annualized_return / max_dd if max_dd > 0 else 0.0

    avg_win = total_win / len(wins) if wins else 0.0
    avg_loss = total_loss / len(losses) if losses else 0.0

    return PerformanceReport(
        total_return=total_return * 100,
        annualized_return=annualized_return * 100,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        max_drawdown=max_dd * 100,
        max_drawdown_duration_days=max_dd_duration,
        win_rate=win_rate * 100,
        profit_factor=profit_factor,
        calmar_ratio=calmar,
        total_trades=total_trades,
        avg_win=avg_win,
        avg_loss=avg_loss,
    )


def calculate_sortino_ratio(
    equity_curve: list[dict[str, Any]],
    risk_free_rate: float = 0.04,
) -> float:
    """Calculate annualized Sortino ratio (uses downside deviation only)."""
    if len(equity_curve) < 2:
        return 0.0

    daily_returns: list[float] = []
    for i in range(1, len(equity_curve)):
        prev = equity_curve[i - 1]["value"]
        curr = equity_curve[i]["value"]
        if prev > 0:
            daily_returns.append((curr - prev) / prev)

    if not daily_returns:
        return 0.0

    avg_return = sum(daily_returns) / len(daily_returns)
    daily_rf = risk_free_rate / 252

    # Downside deviation: only negative returns
    downside_returns = [r - daily_rf for r in daily_returns if r < daily_rf]
    if not downside_returns:
        return 999.0 if avg_return > daily_rf else 0.0

    downside_variance = sum(r ** 2 for r in downside_returns) / len(daily_returns)
    downside_dev = math.sqrt(downside_variance)

    if downside_dev == 0:
        return 0.0

    return ((avg_return - daily_rf) / downside_dev) * math.sqrt(252)


def calculate_calmar_ratio(
    annualized_return: float,
    max_drawdown: float,
) -> float:
    """Calculate Calmar ratio = annualized return / max drawdown."""
    if max_drawdown <= 0:
        return 0.0
    return annualized_return / max_drawdown


def calculate_max_drawdown_duration(
    equity_curve: list[dict[str, Any]],
) -> int:
    """Calculate the maximum drawdown duration in days."""
    if not equity_curve:
        return 0

    peak_idx = 0
    max_duration = 0
    current_duration = 0

    for i in range(len(equity_curve)):
        value = equity_curve[i]["value"]
        peak_value = equity_curve[peak_idx]["value"]

        if value >= peak_value:
            peak_idx = i
            current_duration = 0
        else:
            current_duration = i - peak_idx
            if current_duration > max_duration:
                max_duration = current_duration

    return max_duration


def calculate_monthly_returns(
    equity_curve: list[dict[str, Any]],
) -> list[dict[str, float]]:
    """Calculate monthly returns from equity curve.

    Returns list of {month: str, return: float} for each month.
    """
    if not equity_curve:
        return []

    from datetime import datetime

    # Group equity curve points by month
    monthly: dict[str, list[float]] = {}
    for point in equity_curve:
        date_str = point["date"]
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue
        month_key = dt.strftime("%Y-%m")
        if month_key not in monthly:
            monthly[month_key] = []
        monthly[month_key].append(point["value"])

    # Calculate return for each month
    result: list[dict[str, float]] = []
    for month_key in sorted(monthly.keys()):
        values = monthly[month_key]
        if len(values) >= 2:
            month_return = (values[-1] - values[0]) / values[0] * 100
        else:
            month_return = 0.0
        result.append({
            "month": month_key,
            "return": month_return,
        })

    return result


def _empty_metrics() -> dict[str, float]:
    """Return zeroed metrics."""
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


def _calculate_max_drawdown(equity_curve: list[dict[str, Any]]) -> float:
    """Calculate maximum drawdown from equity curve."""
    peak = 0.0
    max_dd = 0.0
    for point in equity_curve:
        value = point["value"]
        if value > peak:
            peak = value
        if peak > 0:
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
    return max_dd


def _calculate_sharpe_ratio(equity_curve: list[dict[str, Any]], risk_free_rate: float = 0.02) -> float:
    """Calculate annualized Sharpe ratio from equity curve.

    Uses daily returns, assumes 252 trading days per year.
    """
    if len(equity_curve) < 2:
        return 0.0

    daily_returns: list[float] = []
    for i in range(1, len(equity_curve)):
        prev = equity_curve[i - 1]["value"]
        curr = equity_curve[i]["value"]
        if prev > 0:
            daily_returns.append((curr - prev) / prev)

    if not daily_returns:
        return 0.0

    avg_return = sum(daily_returns) / len(daily_returns)
    variance = sum((r - avg_return) ** 2 for r in daily_returns) / len(daily_returns)
    std_dev = math.sqrt(variance)

    if std_dev == 0:
        return 0.0

    # Annualized Sharpe
    daily_rf = risk_free_rate / 252
    return ((avg_return - daily_rf) / std_dev) * math.sqrt(252)

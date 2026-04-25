"""Backtest API routes."""

from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter()


class BacktestRequest(BaseModel):
    """Backtest request payload."""

    symbol: str = Field(..., min_length=1, max_length=10)
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    initial_capital: float = Field(default=100000.0, gt=0)
    short_window: int = Field(default=20, ge=5, le=200)
    long_window: int = Field(default=50, ge=10, le=500)
    strategy: str = Field(default="sma_crossover")
    signal_type: str = Field(default="sma_crossover")
    rsi_period: int = Field(default=14, ge=2, le=50)
    rsi_overbought: float = Field(default=70.0, ge=50.0, le=95.0)
    rsi_oversold: float = Field(default=30.0, ge=5.0, le=50.0)


class TradeResponse(BaseModel):
    """Single trade in response."""

    date: str
    type: str  # "entry" | "exit"
    price: float
    pnl: float | None = None
    pnlPercent: float | None = None


class BacktestMetrics(BaseModel):
    """Performance metrics."""

    totalReturn: float
    annualizedReturn: float
    winRate: float
    profitFactor: float
    maxDrawdown: float
    sharpeRatio: float
    totalTrades: float
    avgWin: float
    avgLoss: float
    bestTrade: float
    worstTrade: float


class MonthlyReturn(BaseModel):
    """Monthly return entry."""

    model_config = ConfigDict(populate_by_name=True)

    month: str
    return_: float = Field(..., alias="return")


class EquityPoint(BaseModel):
    """Single equity curve point."""

    date: str
    value: float
    benchmark: float


class BacktestResponse(BaseModel):
    """Backtest result response."""

    symbol: str
    strategy: str
    equityCurve: list[EquityPoint]
    trades: list[TradeResponse]
    metrics: BacktestMetrics
    monthlyReturns: list[MonthlyReturn]


def _to_camel_case_metrics(metrics: dict[str, float]) -> dict[str, float]:
    """Convert snake_case metrics to camelCase for frontend."""
    return {
        "totalReturn": metrics["total_return"],
        "annualizedReturn": metrics["annualized_return"],
        "winRate": metrics["win_rate"],
        "profitFactor": metrics["profit_factor"],
        "maxDrawdown": metrics["max_drawdown"],
        "sharpeRatio": metrics["sharpe_ratio"],
        "totalTrades": metrics["total_trades"],
        "avgWin": metrics["avg_win"],
        "avgLoss": metrics["avg_loss"],
        "bestTrade": metrics["best_trade"],
        "worstTrade": metrics["worst_trade"],
    }


@router.post("/backtest", response_model=BacktestResponse)
async def run_backtest(request: BacktestRequest) -> BacktestResponse:
    """Run a backtest for the given symbol and date range."""
    try:
        start = date.fromisoformat(request.start_date)
        end = date.fromisoformat(request.end_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")

    if start >= end:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")

    from src.backtest import BacktestEngine

    engine = BacktestEngine(
        short_window=request.short_window,
        long_window=request.long_window,
        signal_type=request.signal_type,
        rsi_period=request.rsi_period,
        rsi_overbought=request.rsi_overbought,
        rsi_oversold=request.rsi_oversold,
    )

    try:
        result = await engine.run_backtest(
            symbol=request.symbol.upper(),
            start_date=start,
            end_date=end,
            initial_capital=request.initial_capital,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest failed: {e}")

    # Map trades to frontend format
    trades_resp: list[TradeResponse] = []
    for t in result.trades:
        if t.status == "closed":
            trades_resp.append(
                TradeResponse(
                    date=t.exit_date or t.entry_date,
                    type="exit",
                    price=t.exit_price or 0.0,
                    pnl=t.pnl,
                    pnlPercent=t.pnl_percent,
                )
            )
        elif t.status == "open":
            trades_resp.append(
                TradeResponse(
                    date=t.entry_date,
                    type="entry",
                    price=t.entry_price,
                )
            )

    # Map equity curve
    equity_curve = [
        EquityPoint(date=p["date"], value=p["value"], benchmark=p["benchmark"])
        for p in result.equity_curve
    ]

    # Map monthly returns
    monthly_returns = [
        MonthlyReturn(month=m["month"], return_=m["return"])  # type: ignore[arg-type]
        for m in result.monthly_returns
    ]

    # Convert metrics to camelCase
    camel_metrics = _to_camel_case_metrics(result.metrics)

    return BacktestResponse(
        symbol=result.symbol,
        strategy=request.strategy,
        equityCurve=equity_curve,
        trades=trades_resp,
        metrics=BacktestMetrics(**camel_metrics),
        monthlyReturns=monthly_returns,
    )

"""Backtest API routes."""

import logging
from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)
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

    # Auto-save to storage
    try:
        from src.backtest.storage import BacktestStorage
        storage = BacktestStorage()
        storage.save({
            "symbol": result.symbol,
            "strategy": request.strategy,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "initial_capital": request.initial_capital,
            "final_capital": equity_curve[-1]["value"] if equity_curve else request.initial_capital,
            "metrics": result.metrics,
            "trades": [
                {
                    "date": t.date,
                    "type": t.type,
                    "price": t.price,
                    "pnl": t.pnl,
                    "pnlPercent": t.pnlPercent,
                }
                for t in trades_resp
            ],
            "equity_curve": [
                {"date": p.date, "value": p.value, "benchmark": p.benchmark}
                for p in equity_curve
            ],
        })
    except Exception:
        logger.warning("Failed to save backtest result to storage", exc_info=True)

    return BacktestResponse(
        symbol=result.symbol,
        strategy=request.strategy,
        equityCurve=equity_curve,
        trades=trades_resp,
        metrics=BacktestMetrics(**camel_metrics),
        monthlyReturns=monthly_returns,
    )


# ─── Backtest History ────────────────────────────────────────────────────────


@router.get("/backtest/history")
async def list_backtest_runs(symbol: str | None = None, limit: int = 50) -> dict:
    """List saved backtest runs, optionally filtered by symbol."""
    from src.backtest.storage import BacktestStorage
    storage = BacktestStorage()
    runs = storage.list_runs(symbol=symbol, limit=limit)
    return {"runs": runs}


@router.get("/backtest/history/{run_id}")
async def get_backtest_run(run_id: str) -> dict:
    """Get full backtest result by run ID."""
    from src.backtest.storage import BacktestStorage
    storage = BacktestStorage()
    result = storage.get_run(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return result


@router.delete("/backtest/history/{run_id}")
async def delete_backtest_run(run_id: str) -> dict:
    """Delete a backtest run."""
    from src.backtest.storage import BacktestStorage
    storage = BacktestStorage()
    if not storage.delete_run(run_id):
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return {"deleted": True}

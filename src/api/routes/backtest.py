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
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}") from e

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
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest failed: {e}") from e

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


# ─── Backtest v3: Walk-Forward API ───────────────────────────────────────────


class WalkForwardRequest(BaseModel):
    """Walk-forward backtest request payload."""

    symbol: str = Field(..., min_length=1, max_length=10)
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    train_window_days: int = Field(default=120, ge=30, le=3650)
    test_window_days: int = Field(default=20, ge=5, le=365)
    step_size_days: int = Field(default=20, ge=1, le=365)
    mode: str = Field(default="rolling", pattern=r"^(rolling|anchored)$")
    strategy: str = Field(default="pipeline")
    initial_capital: float = Field(default=100000.0, gt=0)


class WalkForwardRunSummary(BaseModel):
    """Summary of a walk-forward backtest run."""

    run_id: str
    symbol: str
    strategy: str
    mode: str
    start_date: str
    end_date: str
    total_folds: int
    oos_total_return: float | None = None
    oos_sharpe_ratio: float | None = None
    status: str
    created_at: str | None = None


class WalkForwardRunList(BaseModel):
    """List of walk-forward runs."""

    runs: list[WalkForwardRunSummary]


@router.post("/backtest/runs", status_code=202)
async def submit_walkforward_run(request: WalkForwardRequest) -> dict:
    """Submit a walk-forward backtest run (async).

    Returns the run_id immediately. The backtest runs in the background.
    Poll GET /backtest/runs/{run_id} for results.
    """
    try:
        start = date.fromisoformat(request.start_date)
        end = date.fromisoformat(request.end_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}") from e

    if start >= end:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")

    # Generate demo data
    import random

    from src.backtest.storage import BacktestStorage
    from src.backtest.walk_forward import WalkForwardRunner
    from src.models.backtest import WalkForwardConfig
    random.seed(42)

    from dataclasses import dataclass
    from datetime import datetime, timedelta

    @dataclass
    class _Bar:
        timestamp: datetime
        open: float
        high: float
        low: float
        close: float
        volume: int

    n_days = (end - start).days + 1
    price = 100.0 + hash(request.symbol) % 200
    data = []
    for i in range(n_days):
        change = random.uniform(-2, 2)
        price += change
        if price < 1:
            price = 1
        ts = datetime(start.year, start.month, start.day) + timedelta(days=i)
        data.append(_Bar(timestamp=ts, open=price - 0.5, high=price + 1, low=price - 1, close=price, volume=10000))

    config = WalkForwardConfig(
        train_window_days=request.train_window_days,
        test_window_days=request.test_window_days,
        step_size_days=request.step_size_days,
        mode=request.mode,
    )

    runner = WalkForwardRunner(request.symbol.upper(), config, {"strategy": request.strategy})
    result = await runner.run(data)

    storage = BacktestStorage()
    run_id = storage.save_walkforward(result)

    return {
        "run_id": run_id,
        "symbol": request.symbol.upper(),
        "status": "completed",
        "total_folds": len(result.folds),
    }


@router.get("/backtest/runs", response_model=WalkForwardRunList)
async def list_walkforward_runs(symbol: str | None = None, limit: int = 50) -> dict:
    """List walk-forward backtest runs."""
    from src.backtest.storage import BacktestStorage
    storage = BacktestStorage()
    runs = storage.list_walkforward_runs(symbol=symbol, limit=limit)
    return {"runs": runs}


@router.get("/backtest/runs/{run_id}")
async def get_walkforward_run(run_id: str) -> dict:
    """Get a walk-forward backtest run by ID."""
    from src.backtest.storage import BacktestStorage
    storage = BacktestStorage()
    result = storage.get_walkforward(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Walk-forward run not found")
    return result


@router.get("/backtest/runs/{run_id}/report")
async def get_walkforward_report(run_id: str) -> dict:
    """Get the HTML report for a walk-forward backtest run."""
    from src.backtest.report import render_walkforward_report
    from src.backtest.storage import BacktestStorage
    from src.models.backtest import (
        FoldResult,
        PerformanceReport,
        PipelineBacktestResult,
        WalkForwardConfig,
        WalkForwardResult,
    )

    storage = BacktestStorage()
    data = storage.get_walkforward(run_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Walk-forward run not found")

    # Reconstruct WalkForwardResult from stored data
    folds = []
    for f in data["folds"]:
        train_result = PipelineBacktestResult(
            symbol=data["symbol"],
            strategy=data["strategy"],
            start_date=date.fromisoformat(f["train_start"]),
            end_date=date.fromisoformat(f["train_end"]),
            metrics=PerformanceReport(
                sharpe_ratio=f["train_sharpe"] or 0,
            ),
        )
        test_result = PipelineBacktestResult(
            symbol=data["symbol"],
            strategy=data["strategy"],
            start_date=date.fromisoformat(f["test_start"]),
            end_date=date.fromisoformat(f["test_end"]),
            metrics=PerformanceReport(
                sharpe_ratio=f["test_sharpe"] or 0,
                total_return=f["test_return"] or 0,
                max_drawdown=f["test_max_drawdown"] or 0,
                total_trades=f["test_trades"] or 0,
            ),
        )
        folds.append(FoldResult(
            fold_index=f["fold_index"],
            train_start=date.fromisoformat(f["train_start"]),
            train_end=date.fromisoformat(f["train_end"]),
            test_start=date.fromisoformat(f["test_start"]),
            test_end=date.fromisoformat(f["test_end"]),
            train_result=train_result,
            test_result=test_result,
        ))

    config = WalkForwardConfig(
        train_window_days=data["train_window_days"],
        test_window_days=data["test_window_days"],
        step_size_days=data["step_size_days"],
        mode=data["mode"],
    )

    wf_result = WalkForwardResult(
        symbol=data["symbol"],
        config=config,
        folds=folds,
        aggregate_metrics=PerformanceReport(
            total_return=data["oos_total_return"] or 0,
            sharpe_ratio=data["oos_sharpe_ratio"] or 0,
            max_drawdown=data["oos_max_drawdown"] or 0,
            win_rate=data["oos_win_rate"] or 0,
        ),
    )

    html = render_walkforward_report(wf_result)
    return {"run_id": run_id, "html": html}

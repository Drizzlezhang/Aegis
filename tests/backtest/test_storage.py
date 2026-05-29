"""Tests for backtest storage."""

import tempfile
from datetime import date
from pathlib import Path

from src.backtest.storage import BacktestStorage
from src.models.backtest import (
    FoldResult,
    PerformanceReport,
    PipelineBacktestResult,
    PipelineBacktestTrade,
    WalkForwardConfig,
    WalkForwardResult,
)


class TestBacktestStorage:
    """Tests for BacktestStorage."""

    def test_save_and_retrieve(self):
        """Save a result and retrieve it by ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = BacktestStorage(storage_dir=Path(tmpdir))
            result = {
                "symbol": "AAPL",
                "strategy": "covered_call",
                "start_date": "2024-01-01",
                "end_date": "2024-06-01",
                "initial_capital": 100000.0,
                "final_capital": 105000.0,
                "metrics": {
                    "total_return": 5.0,
                    "max_drawdown": -3.0,
                    "total_trades": 10,
                },
                "trades": [],
                "equity_curve": [],
            }

            run_id = storage.save(result)
            assert len(run_id) == 12

            retrieved = storage.get_run(run_id)
            assert retrieved is not None
            assert retrieved["symbol"] == "AAPL"
            assert retrieved["strategy"] == "covered_call"
            assert retrieved["metrics"]["total_return"] == 5.0

    def test_list_runs_with_filter(self):
        """List runs filtered by symbol."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = BacktestStorage(storage_dir=Path(tmpdir))

            storage.save({
                "symbol": "AAPL",
                "strategy": "covered_call",
                "start_date": "2024-01-01",
                "end_date": "2024-06-01",
                "initial_capital": 100000.0,
                "final_capital": 105000.0,
                "metrics": {"total_return": 5.0, "max_drawdown": -3.0, "total_trades": 10},
            })
            storage.save({
                "symbol": "GOOGL",
                "strategy": "bull_spread",
                "start_date": "2024-01-01",
                "end_date": "2024-06-01",
                "initial_capital": 100000.0,
                "final_capital": 110000.0,
                "metrics": {"total_return": 10.0, "max_drawdown": -5.0, "total_trades": 5},
            })

            all_runs = storage.list_runs()
            assert len(all_runs) == 2

            aapl_runs = storage.list_runs(symbol="AAPL")
            assert len(aapl_runs) == 1
            assert aapl_runs[0]["symbol"] == "AAPL"

            googl_runs = storage.list_runs(symbol="googl")  # case insensitive
            assert len(googl_runs) == 1
            assert googl_runs[0]["symbol"] == "GOOGL"

    def test_delete_run(self):
        """Delete a run and verify it's gone."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = BacktestStorage(storage_dir=Path(tmpdir))

            run_id = storage.save({
                "symbol": "AAPL",
                "strategy": "covered_call",
                "start_date": "2024-01-01",
                "end_date": "2024-06-01",
                "initial_capital": 100000.0,
                "final_capital": 105000.0,
                "metrics": {"total_return": 5.0, "max_drawdown": -3.0, "total_trades": 10},
            })

            assert storage.get_run(run_id) is not None

            deleted = storage.delete_run(run_id)
            assert deleted is True

            assert storage.get_run(run_id) is None

            # Delete non-existent
            assert storage.delete_run("nonexistent") is False


class TestWalkforwardStorage:
    """T14: Walk-forward persistence — save_walkforward, get_walkforward, list_walkforward_runs."""

    def _make_wf_result(self) -> WalkForwardResult:
        """Create a sample WalkForwardResult with folds and trades."""
        equity = [
            {"date": "2024-01-02", "value": 100000.0},
            {"date": "2024-01-03", "value": 101000.0},
        ]
        trade = PipelineBacktestTrade(
            entry_date="2024-01-02",
            exit_date="2024-01-03",
            entry_price=100.0,
            exit_price=101.0,
            shares=100,
            pnl=100.0,
            pnl_percent=1.0,
            status="closed",
            entry_phase="markup",
            exit_phase="distribution",
            entry_confidence=75.0,
            exit_confidence=60.0,
        )
        train_result = PipelineBacktestResult(
            symbol="QQQ", strategy="pipeline",
            start_date=date(2024, 1, 1), end_date=date(2024, 1, 15),
            equity_curve=equity,
            metrics=PerformanceReport(sharpe_ratio=1.5, total_return=3.0),
        )
        test_result = PipelineBacktestResult(
            symbol="QQQ", strategy="pipeline",
            start_date=date(2024, 1, 16), end_date=date(2024, 1, 31),
            equity_curve=equity,
            trades=[trade],
            metrics=PerformanceReport(sharpe_ratio=1.2, total_return=2.0, max_drawdown=1.0, total_trades=1),
        )
        fold = FoldResult(
            fold_index=0,
            train_start=date(2024, 1, 1), train_end=date(2024, 1, 15),
            test_start=date(2024, 1, 16), test_end=date(2024, 1, 31),
            train_result=train_result, test_result=test_result,
        )
        config = WalkForwardConfig(
            train_window_days=15, test_window_days=15, step_size_days=15,
        )
        return WalkForwardResult(
            symbol="QQQ", config=config, folds=[fold],
            aggregate_metrics=PerformanceReport(total_return=2.0, sharpe_ratio=1.2, max_drawdown=1.0, win_rate=100.0),
            oos_equity_curve=equity,
        )

    def test_save_and_retrieve_walkforward(self):
        """save_walkforward persists and get_walkforward retrieves correctly."""
        storage = BacktestStorage()
        result = self._make_wf_result()

        run_id = storage.save_walkforward(result)
        assert len(run_id) == 12

        retrieved = storage.get_walkforward(run_id)
        assert retrieved is not None
        assert retrieved["symbol"] == "QQQ"
        assert retrieved["mode"] == "rolling"
        assert retrieved["total_folds"] == 1
        assert retrieved["oos_sharpe_ratio"] == 1.2
        assert len(retrieved["folds"]) == 1
        assert retrieved["folds"][0]["fold_index"] == 0
        assert retrieved["folds"][0]["test_sharpe"] == 1.2
        assert len(retrieved["trades"]) == 1
        assert retrieved["trades"][0]["pnl"] == 100.0

    def test_get_walkforward_not_found(self):
        """get_walkforward returns None for non-existent run_id."""
        storage = BacktestStorage()
        result = storage.get_walkforward("nonexistent123")
        assert result is None

    def test_list_walkforward_runs(self):
        """list_walkforward_runs returns saved runs."""
        storage = BacktestStorage()
        result = self._make_wf_result()

        run_id = storage.save_walkforward(result)

        runs = storage.list_walkforward_runs()
        assert len(runs) >= 1
        assert any(r["run_id"] == run_id for r in runs)

    def test_list_walkforward_runs_filtered(self):
        """list_walkforward_runs filters by symbol."""
        storage = BacktestStorage()
        result = self._make_wf_result()

        storage.save_walkforward(result)

        runs = storage.list_walkforward_runs(symbol="QQQ")
        assert len(runs) >= 1
        assert all(r["symbol"] == "QQQ" for r in runs)

        runs_other = storage.list_walkforward_runs(symbol="NONEXIST")
        assert len(runs_other) == 0

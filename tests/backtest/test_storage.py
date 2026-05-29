"""Tests for backtest storage."""

import tempfile
from pathlib import Path

from src.backtest.storage import BacktestStorage


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

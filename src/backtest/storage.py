"""Backtest result persistence."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Session, relationship

from src.models.backtest import WalkForwardResult

STORAGE_DIR = Path.home() / ".aegis-trader" / "backtests"


class Base(DeclarativeBase):
    pass


class BacktestRunORM(Base):
    """ORM model for backtest v3 runs (walk-forward)."""

    __tablename__ = "backtest_v3_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), unique=True, nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    strategy = Column(String(100), nullable=False)
    mode = Column(String(20), nullable=False)  # rolling | anchored
    train_window_days = Column(Integer, nullable=False)
    test_window_days = Column(Integer, nullable=False)
    step_size_days = Column(Integer, nullable=False)
    start_date = Column(String(10), nullable=False)
    end_date = Column(String(10), nullable=False)
    total_folds = Column(Integer, nullable=False)
    oos_total_return = Column(Float, nullable=True)
    oos_sharpe_ratio = Column(Float, nullable=True)
    oos_max_drawdown = Column(Float, nullable=True)
    oos_win_rate = Column(Float, nullable=True)
    status = Column(String(20), default="completed")  # running | completed | failed
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    folds = relationship("BacktestFoldORM", back_populates="run", cascade="all, delete-orphan")


class BacktestFoldORM(Base):
    """ORM model for a single walk-forward fold."""

    __tablename__ = "backtest_v3_folds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("backtest_v3_runs.id"), nullable=False, index=True)
    fold_index = Column(Integer, nullable=False)
    train_start = Column(String(10), nullable=False)
    train_end = Column(String(10), nullable=False)
    test_start = Column(String(10), nullable=False)
    test_end = Column(String(10), nullable=False)
    train_sharpe = Column(Float, nullable=True)
    test_sharpe = Column(Float, nullable=True)
    test_return = Column(Float, nullable=True)
    test_max_drawdown = Column(Float, nullable=True)
    test_trades = Column(Integer, nullable=True)

    run = relationship("BacktestRunORM", back_populates="folds")


class BacktestTradeORM(Base):
    """ORM model for individual backtest trades."""

    __tablename__ = "backtest_v3_trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("backtest_v3_runs.id"), nullable=False, index=True)
    fold_index = Column(Integer, nullable=True)
    entry_date = Column(String(10), nullable=False)
    exit_date = Column(String(10), nullable=True)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    shares = Column(Integer, nullable=False)
    pnl = Column(Float, nullable=True)
    pnl_percent = Column(Float, nullable=True)
    status = Column(String(20), nullable=False)
    entry_phase = Column(String(50), nullable=True)
    exit_phase = Column(String(50), nullable=True)
    entry_confidence = Column(Float, nullable=True)
    exit_confidence = Column(Float, nullable=True)


class BacktestStorage:
    """SQLite index + JSON file storage for backtest results."""

    def __init__(self, storage_dir: Path | None = None):
        self._dir = storage_dir or STORAGE_DIR
        self._dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self._dir / "index.db"
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS backtest_runs (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    start_date TEXT,
                    end_date TEXT,
                    initial_capital REAL,
                    final_capital REAL,
                    total_return REAL,
                    max_drawdown REAL,
                    total_trades INTEGER,
                    created_at TEXT NOT NULL
                )
            """)

    def save(self, result: dict) -> str:
        """Save backtest result, return run ID."""
        run_id = uuid4().hex[:12]
        # Write full result to JSON
        result_path = self._dir / f"{run_id}.json"
        result_path.write_text(json.dumps(result, default=str, indent=2))
        # Index in SQLite
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                "INSERT INTO backtest_runs VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    run_id,
                    result["symbol"],
                    result["strategy"],
                    result.get("start_date"),
                    result.get("end_date"),
                    result.get("initial_capital"),
                    result.get("final_capital"),
                    result.get("metrics", {}).get("total_return"),
                    result.get("metrics", {}).get("max_drawdown"),
                    result.get("metrics", {}).get("total_trades"),
                    datetime.now(UTC).isoformat(),
                ),
            )
        return run_id

    def list_runs(self, symbol: str | None = None, limit: int = 50) -> list[dict]:
        """List recent backtest runs, optionally filtered by symbol."""
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            if symbol:
                rows = conn.execute(
                    "SELECT * FROM backtest_runs WHERE symbol = ? ORDER BY created_at DESC LIMIT ?",
                    (symbol.upper(), limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM backtest_runs ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [dict(r) for r in rows]

    def get_run(self, run_id: str) -> dict | None:
        """Get full backtest result by ID."""
        result_path = self._dir / f"{run_id}.json"
        if not result_path.exists():
            return None
        return json.loads(result_path.read_text())

    def delete_run(self, run_id: str) -> bool:
        """Delete a backtest run. Returns True if deleted, False if not found."""
        result_path = self._dir / f"{run_id}.json"
        if not result_path.exists():
            return False
        result_path.unlink()
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("DELETE FROM backtest_runs WHERE id = ?", (run_id,))
        return True

    # ── Backtest v3: Walk-Forward Persistence ──────────────────────

    def _get_orm_session(self) -> Session:
        """Create a SQLAlchemy session using the app database URL."""
        import os

        from sqlalchemy import create_engine

        from src.config import get_config

        url = get_config().database.url
        if url.startswith("sqlite:///"):
            path = url[len("sqlite:///"):]
            path = os.path.expanduser(path)
            url = f"sqlite:///{path}"
        engine = create_engine(url)
        return Session(engine)

    def save_walkforward(self, result: "WalkForwardResult") -> str:
        """Save a walk-forward backtest result to the database.

        Args:
            result: WalkForwardResult to persist.

        Returns:
            The run_id string.
        """

        run_id = uuid4().hex[:12]
        session = self._get_orm_session()
        try:
            m = result.aggregate_metrics
            run = BacktestRunORM(
                run_id=run_id,
                symbol=result.symbol,
                strategy="pipeline",
                mode=result.config.mode,
                train_window_days=result.config.train_window_days,
                test_window_days=result.config.test_window_days,
                step_size_days=result.config.step_size_days,
                start_date=result.folds[0].train_start.isoformat() if result.folds else "",
                end_date=result.folds[-1].test_end.isoformat() if result.folds else "",
                total_folds=len(result.folds),
                oos_total_return=m.total_return,
                oos_sharpe_ratio=m.sharpe_ratio,
                oos_max_drawdown=m.max_drawdown,
                oos_win_rate=m.win_rate,
            )
            session.add(run)
            session.flush()  # get run.id

            for fold in result.folds:
                fold_orm = BacktestFoldORM(
                    run_id=run.id,
                    fold_index=fold.fold_index,
                    train_start=fold.train_start.isoformat(),
                    train_end=fold.train_end.isoformat(),
                    test_start=fold.test_start.isoformat(),
                    test_end=fold.test_end.isoformat(),
                    train_sharpe=fold.train_result.metrics.sharpe_ratio,
                    test_sharpe=fold.test_result.metrics.sharpe_ratio,
                    test_return=fold.test_result.metrics.total_return,
                    test_max_drawdown=fold.test_result.metrics.max_drawdown,
                    test_trades=fold.test_result.metrics.total_trades,
                )
                session.add(fold_orm)

                for trade in fold.test_result.trades:
                    trade_orm = BacktestTradeORM(
                        run_id=run.id,
                        fold_index=fold.fold_index,
                        entry_date=trade.entry_date,
                        exit_date=trade.exit_date,
                        entry_price=trade.entry_price,
                        exit_price=trade.exit_price,
                        shares=trade.shares,
                        pnl=trade.pnl,
                        pnl_percent=trade.pnl_percent,
                        status=trade.status,
                        entry_phase=trade.entry_phase,
                        exit_phase=trade.exit_phase,
                        entry_confidence=trade.entry_confidence,
                        exit_confidence=trade.exit_confidence,
                    )
                    session.add(trade_orm)

            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

        return run_id

    def get_walkforward(self, run_id: str) -> dict | None:
        """Retrieve a walk-forward backtest result by run_id.

        Args:
            run_id: The run_id string.

        Returns:
            Dict with run, folds, and trades data, or None if not found.
        """
        session = self._get_orm_session()
        try:
            run = session.query(BacktestRunORM).filter_by(run_id=run_id).first()
            if run is None:
                return None

            folds = session.query(BacktestFoldORM).filter_by(run_id=run.id).order_by(BacktestFoldORM.fold_index).all()
            trades = session.query(BacktestTradeORM).filter_by(run_id=run.id).order_by(BacktestTradeORM.id).all()

            return {
                "run_id": run.run_id,
                "symbol": run.symbol,
                "strategy": run.strategy,
                "mode": run.mode,
                "train_window_days": run.train_window_days,
                "test_window_days": run.test_window_days,
                "step_size_days": run.step_size_days,
                "start_date": run.start_date,
                "end_date": run.end_date,
                "total_folds": run.total_folds,
                "oos_total_return": run.oos_total_return,
                "oos_sharpe_ratio": run.oos_sharpe_ratio,
                "oos_max_drawdown": run.oos_max_drawdown,
                "oos_win_rate": run.oos_win_rate,
                "status": run.status,
                "created_at": run.created_at.isoformat() if run.created_at else None,
                "folds": [
                    {
                        "fold_index": f.fold_index,
                        "train_start": f.train_start,
                        "train_end": f.train_end,
                        "test_start": f.test_start,
                        "test_end": f.test_end,
                        "train_sharpe": f.train_sharpe,
                        "test_sharpe": f.test_sharpe,
                        "test_return": f.test_return,
                        "test_max_drawdown": f.test_max_drawdown,
                        "test_trades": f.test_trades,
                    }
                    for f in folds
                ],
                "trades": [
                    {
                        "fold_index": t.fold_index,
                        "entry_date": t.entry_date,
                        "exit_date": t.exit_date,
                        "entry_price": t.entry_price,
                        "exit_price": t.exit_price,
                        "shares": t.shares,
                        "pnl": t.pnl,
                        "pnl_percent": t.pnl_percent,
                        "status": t.status,
                        "entry_phase": t.entry_phase,
                        "exit_phase": t.exit_phase,
                    }
                    for t in trades
                ],
            }
        finally:
            session.close()

    def list_walkforward_runs(self, symbol: str | None = None, limit: int = 50) -> list[dict]:
        """List recent walk-forward backtest runs.

        Args:
            symbol: Optional symbol filter.
            limit: Maximum number of runs to return.

        Returns:
            List of run summary dicts.
        """
        session = self._get_orm_session()
        try:
            q = session.query(BacktestRunORM).order_by(BacktestRunORM.created_at.desc())
            if symbol:
                q = q.filter(BacktestRunORM.symbol == symbol.upper())
            runs = q.limit(limit).all()
            return [
                {
                    "run_id": r.run_id,
                    "symbol": r.symbol,
                    "strategy": r.strategy,
                    "mode": r.mode,
                    "start_date": r.start_date,
                    "end_date": r.end_date,
                    "total_folds": r.total_folds,
                    "oos_total_return": r.oos_total_return,
                    "oos_sharpe_ratio": r.oos_sharpe_ratio,
                    "status": r.status,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in runs
            ]
        finally:
            session.close()

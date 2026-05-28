"""Scheduler execution history ORM model and CRUD operations."""

import os
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Session

from src.config import get_config


class Base(DeclarativeBase):
    pass


class SchedulerHistory(Base):
    __tablename__ = "scheduler_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(255), nullable=False, index=True)
    status = Column(String(20), nullable=False)  # SUCCESS / FAILED / SKIPPED
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    error_msg = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


def _resolve_db_url() -> str:
    """Resolve database URL with expanded user path."""
    url = get_config().database.url
    if url.startswith("sqlite:///"):
        path = url[len("sqlite:///"):]
        path = os.path.expanduser(path)
        url = f"sqlite:///{path}"
    return url


def get_session() -> Session:
    """Create a new SQLAlchemy session from config."""
    engine = create_engine(_resolve_db_url())
    return Session(engine)


def record_start(session: Session, job_id: str) -> int:
    """Record job start and return the history row ID."""
    entry = SchedulerHistory(
        job_id=job_id,
        status="RUNNING",
        start_at=datetime.now(UTC),
    )
    session.add(entry)
    session.commit()
    return entry.id  # type: ignore[no-any-return]


def record_end(
    session: Session,
    history_id: int,
    status: str,
    duration_ms: int,
    error_msg: str | None = None,
) -> None:
    """Update a history entry with end status and duration."""
    entry = session.get(SchedulerHistory, history_id)
    if entry is None:
        return
    entry.status = status
    entry.end_at = datetime.now(UTC)
    entry.duration_ms = duration_ms
    if error_msg:
        entry.error_msg = error_msg
    session.commit()


def record_skipped(session: Session, job_id: str) -> None:
    """Record a skipped execution (overlapping run)."""
    entry = SchedulerHistory(
        job_id=job_id,
        status="SKIPPED",
        start_at=datetime.now(UTC),
        end_at=datetime.now(UTC),
        duration_ms=0,
    )
    session.add(entry)
    session.commit()


def list_history(
    session: Session,
    job_id: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """List recent execution history entries."""
    q = session.query(SchedulerHistory).order_by(SchedulerHistory.start_at.desc())
    if job_id:
        q = q.filter(SchedulerHistory.job_id == job_id)
    rows = q.limit(limit).all()
    return [
        {
            "id": r.id,
            "job_id": r.job_id,
            "status": r.status,
            "start_at": r.start_at.isoformat() if r.start_at else None,
            "end_at": r.end_at.isoformat() if r.end_at else None,
            "duration_ms": r.duration_ms,
            "error_msg": r.error_msg,
        }
        for r in rows
    ]


def cleanup_old(session: Session, retention_days: int = 30) -> int:
    """Delete history entries older than retention_days. Returns count deleted."""
    from datetime import timedelta
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    count = (
        session.query(SchedulerHistory)
        .filter(SchedulerHistory.start_at < cutoff)
        .delete()
    )
    session.commit()
    return count  # type: ignore[no-any-return]

"""Decision tracking service — track whether recommendations hit targets."""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from uuid import uuid4

import yfinance as yf

from src.config import get_config
from .models import TrackedDecision, TrackingStatus

logger = logging.getLogger(__name__)


class TrackingService:
    """Track post-analysis recommendation performance."""

    def __init__(self):
        self._path = Path("~/.aegis-trader/tracked_decisions.json").expanduser()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._decisions: list[TrackedDecision] = self._load()

    def _load(self) -> list[TrackedDecision]:
        if self._path.exists():
            data = json.loads(self._path.read_text())
            return [TrackedDecision(**d) for d in data]
        return []

    def _save(self):
        self._path.write_text(
            json.dumps([d.model_dump(mode="json") for d in self._decisions], indent=2)
        )

    def record_recommendation(
        self,
        symbol: str,
        strategy_type: str,
        entry_price: float,
        target_price: float | None,
        stop_loss: float | None,
        confidence: float,
        expiry_days: int = 30,
    ) -> TrackedDecision:
        """Record a new recommendation and start tracking."""
        decision = TrackedDecision(
            id=str(uuid4())[:8],
            symbol=symbol.upper(),
            strategy_type=strategy_type,
            recommended_at=datetime.now(),
            entry_price=entry_price,
            target_price=target_price,
            stop_loss_price=stop_loss,
            expiry_date=datetime.now() + timedelta(days=expiry_days),
            confidence=confidence,
            status=TrackingStatus.PENDING,
        )
        self._decisions.append(decision)
        self._save()
        return decision

    async def update_all(self):
        """Batch-update all PENDING/ACTIVE tracked decisions."""
        pending = [
            d for d in self._decisions
            if d.status in (TrackingStatus.PENDING, TrackingStatus.ACTIVE)
        ]
        if not pending:
            return

        symbols = list(set(d.symbol for d in pending))
        logger.info(f"Updating {len(pending)} tracked decisions for {len(symbols)} symbols")

        for decision in pending:
            try:
                self._update_one(decision)
            except Exception as e:
                logger.error(f"Failed to update {decision.symbol}/{decision.id}: {e}")

        self._save()

    def _update_one(self, decision: TrackedDecision):
        """Update the status of a single tracked decision."""
        ticker = yf.Ticker(decision.symbol)
        hist = ticker.history(start=decision.recommended_at.strftime("%Y-%m-%d"))
        if hist.empty:
            return

        decision.actual_high = float(hist["High"].max())
        decision.actual_low = float(hist["Low"].min())
        decision.updated_at = datetime.now()

        current_price = float(hist["Close"].iloc[-1])

        if decision.target_price and decision.actual_high >= decision.target_price:
            decision.status = TrackingStatus.HIT_TARGET
            decision.pnl_pct = (decision.target_price - decision.entry_price) / decision.entry_price * 100
            decision.hit_date = datetime.now()
        elif decision.stop_loss_price and decision.actual_low <= decision.stop_loss_price:
            decision.status = TrackingStatus.HIT_STOP
            decision.pnl_pct = (decision.stop_loss_price - decision.entry_price) / decision.entry_price * 100
            decision.hit_date = datetime.now()
        elif decision.expiry_date and datetime.now() > decision.expiry_date:
            decision.status = TrackingStatus.EXPIRED
            decision.actual_price_at_expiry = current_price
            decision.pnl_pct = (current_price - decision.entry_price) / decision.entry_price * 100
        else:
            decision.status = TrackingStatus.ACTIVE

    def get_stats(self) -> dict:
        """Calculate hit rate statistics."""
        completed = [
            d for d in self._decisions
            if d.status not in (TrackingStatus.PENDING, TrackingStatus.ACTIVE)
        ]
        if not completed:
            return {
                "total": 0, "hit_rate": 0, "avg_pnl_pct": 0,
                "by_strategy": {}, "pending": len(self._decisions),
            }

        hits = sum(1 for d in completed if d.status == TrackingStatus.HIT_TARGET)
        avg_pnl = sum(d.pnl_pct or 0 for d in completed) / len(completed)

        by_strategy: dict[str, dict] = {}
        for d in completed:
            key = d.strategy_type
            if key not in by_strategy:
                by_strategy[key] = {"total": 0, "hits": 0}
            by_strategy[key]["total"] += 1
            if d.status == TrackingStatus.HIT_TARGET:
                by_strategy[key]["hits"] += 1

        return {
            "total": len(completed),
            "hit_rate": round(hits / len(completed), 3),
            "avg_pnl_pct": round(avg_pnl, 2),
            "by_strategy": {
                k: {**v, "hit_rate": round(v["hits"] / v["total"], 3)}
                for k, v in by_strategy.items()
            },
            "pending": len([
                d for d in self._decisions
                if d.status in (TrackingStatus.PENDING, TrackingStatus.ACTIVE)
            ]),
        }

    def list_recent(self, limit: int = 20) -> list[TrackedDecision]:
        """Return the most recent tracked decisions."""
        return sorted(self._decisions, key=lambda d: d.recommended_at, reverse=True)[:limit]
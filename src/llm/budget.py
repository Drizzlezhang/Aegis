"""Budget guard for LLM governance.

Provides BudgetMiddleware that checks daily/monthly LLM spending against
configured limits. Triggers warning at 80% and blocks at 100%.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from src.config import get_config
from src.db import get_session

from .middleware import GovernanceAbortError, GovernanceContext, Middleware

logger = logging.getLogger(__name__)


class BudgetExceededError(GovernanceAbortError):
    """Raised when LLM budget is exceeded and the call is blocked."""

    def __init__(self, period: str, limit_usd: float, used_usd: float):
        self.period = period
        self.limit_usd = limit_usd
        self.used_usd = used_usd
        super().__init__(
            f"LLM budget exceeded: {period} limit ${limit_usd:.2f}, "
            f"used ${used_usd:.2f} ({used_usd / limit_usd * 100:.1f}%)"
        )


# ── Budget Tracker ───────────────────────────────────────────────────────────


class BudgetTracker:
    """Tracks LLM spending against daily and monthly budgets."""

    def __init__(
        self,
        daily_limit_usd: float = 10.0,
        monthly_limit_usd: float = 200.0,
    ) -> None:
        self.daily_limit = daily_limit_usd
        self.monthly_limit = monthly_limit_usd
        self._daily_usage: float | None = None
        self._monthly_usage: float | None = None
        self._last_daily_check: float = 0.0
        self._last_monthly_check: float = 0.0
        self._cache_ttl: float = 60.0  # Cache usage for 60 seconds

    async def get_daily_usage(self) -> float:
        """Get total USD spent today (UTC)."""
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        try:
            async with get_session() as session:
                from sqlalchemy import text

                result = await session.execute(
                    text(
                        "SELECT COALESCE(SUM(cost_usd), 0) FROM llm_call_log "
                        "WHERE timestamp >= :start AND success = 1"
                    ),
                    {"start": today_start.isoformat()},
                )
                row = result.fetchone()
                return float(row[0]) if row else 0.0
        except Exception:
            logger.debug("llm_call_log table not available for daily usage")
            return 0.0

    async def get_monthly_usage(self) -> float:
        """Get total USD spent this month (UTC)."""
        now = datetime.now(UTC)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        try:
            async with get_session() as session:
                from sqlalchemy import text

                result = await session.execute(
                    text(
                        "SELECT COALESCE(SUM(cost_usd), 0) FROM llm_call_log "
                        "WHERE timestamp >= :start AND success = 1"
                    ),
                    {"start": month_start.isoformat()},
                )
                row = result.fetchone()
                return float(row[0]) if row else 0.0
        except Exception:
            logger.debug("llm_call_log table not available for monthly usage")
            return 0.0

    async def check(self) -> dict[str, Any]:
        """Check budget status. Returns dict with daily and monthly status."""
        daily_usage = await self.get_daily_usage()
        monthly_usage = await self.get_monthly_usage()

        daily_pct = (daily_usage / self.daily_limit * 100) if self.daily_limit > 0 else 0
        monthly_pct = (monthly_usage / self.monthly_limit * 100) if self.monthly_limit > 0 else 0

        def _status(pct: float) -> str:
            if pct >= 100:
                return "critical"
            if pct >= 80:
                return "warning"
            return "ok"

        return {
            "daily": {
                "limit_usd": self.daily_limit,
                "used_usd": round(daily_usage, 6),
                "remaining_usd": round(max(0, self.daily_limit - daily_usage), 6),
                "pct": round(daily_pct, 2),
                "status": _status(daily_pct),
            },
            "monthly": {
                "limit_usd": self.monthly_limit,
                "used_usd": round(monthly_usage, 6),
                "remaining_usd": round(max(0, self.monthly_limit - monthly_usage), 6),
                "pct": round(monthly_pct, 2),
                "status": _status(monthly_pct),
            },
        }


# ── Budget Middleware ────────────────────────────────────────────────────────


class BudgetMiddleware(Middleware):
    """Middleware that checks budget before allowing LLM calls."""

    def __init__(self, tracker: BudgetTracker | None = None) -> None:
        config = get_config()
        governance = getattr(config.llm, "governance", None)
        daily = getattr(governance, "budget_daily_usd", 10.0) if governance else 10.0
        monthly = getattr(governance, "budget_monthly_usd", 200.0) if governance else 200.0
        self._tracker = tracker or BudgetTracker(
            daily_limit_usd=daily,
            monthly_limit_usd=monthly,
        )

    @property
    def tracker(self) -> BudgetTracker:
        return self._tracker

    async def process(
        self,
        ctx: GovernanceContext,
        call_next: Callable[[GovernanceContext], Awaitable[Any]],
    ) -> Any:
        # Skip budget check if bypass is set
        if ctx.bypass_budget:
            return await call_next(ctx)

        status = await self._tracker.check()

        # Update Prometheus metrics
        try:
            from src.services.metrics import record_llm_budget_usage
            record_llm_budget_usage("daily", status["daily"]["pct"] / 100.0)
            record_llm_budget_usage("monthly", status["monthly"]["pct"] / 100.0)
        except Exception:
            pass

        # Check daily budget first (more restrictive)
        if status["daily"]["status"] == "critical":
            await self._fire_alert("daily", status["daily"], "critical")
            raise BudgetExceededError(
                "daily",
                status["daily"]["limit_usd"],
                status["daily"]["used_usd"],
            )

        if status["daily"]["status"] == "warning":
            await self._fire_alert("daily", status["daily"], "warning")

        # Check monthly budget
        if status["monthly"]["status"] == "critical":
            await self._fire_alert("monthly", status["monthly"], "critical")
            raise BudgetExceededError(
                "monthly",
                status["monthly"]["limit_usd"],
                status["monthly"]["used_usd"],
            )

        if status["monthly"]["status"] == "warning":
            await self._fire_alert("monthly", status["monthly"], "warning")

        return await call_next(ctx)

    async def _fire_alert(
        self, period: str, budget_info: dict[str, Any], severity: str
    ) -> None:
        """Fire an alert via EventBus + AlertEngine."""
        try:
            from src.services.event_bus import BaseEvent, EventSeverity, get_event_bus

            event = BaseEvent(
                source="llm_budget",
                severity=EventSeverity(severity),
            )
            # Attach budget info as attributes
            event.period = period  # type: ignore[attr-defined]
            event.limit_usd = budget_info["limit_usd"]  # type: ignore[attr-defined]
            event.used_usd = budget_info["used_usd"]  # type: ignore[attr-defined]
            event.pct = budget_info["pct"]  # type: ignore[attr-defined]

            bus = get_event_bus()
            bus.publish(event)

            logger.warning(
                "LLM budget %s: %s%% used ($%.2f / $%.2f)",
                period,
                budget_info["pct"],
                budget_info["used_usd"],
                budget_info["limit_usd"],
            )
        except Exception:
            logger.exception("Failed to fire budget alert")


# ── Global Tracker ───────────────────────────────────────────────────────────

_tracker_instance: BudgetTracker | None = None


def get_budget_tracker() -> BudgetTracker:
    """Get or create the global budget tracker."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = BudgetTracker()
    return _tracker_instance


def reset_budget_tracker() -> None:
    """Reset the global budget tracker (for testing)."""
    global _tracker_instance
    _tracker_instance = None

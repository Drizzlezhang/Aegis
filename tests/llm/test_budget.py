"""Tests for LLM budget guard (D5)."""

from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from src.llm.budget import (
    BudgetExceededError,
    BudgetMiddleware,
    BudgetTracker,
    get_budget_tracker,
    reset_budget_tracker,
)
from src.llm.middleware import GovernanceContext


class TestBudgetTracker:
    async def test_initial_check_all_ok(self) -> None:
        tracker = BudgetTracker(daily_limit_usd=10.0, monthly_limit_usd=200.0)
        status = await tracker.check()
        assert status["daily"]["status"] == "ok"
        assert status["monthly"]["status"] == "ok"
        assert status["daily"]["limit_usd"] == 10.0
        assert status["monthly"]["limit_usd"] == 200.0

    async def test_daily_usage_from_db(self) -> None:
        tracker = BudgetTracker(daily_limit_usd=10.0)
        usage = await tracker.get_daily_usage()
        assert isinstance(usage, float)
        assert usage >= 0.0

    async def test_monthly_usage_from_db(self) -> None:
        tracker = BudgetTracker(monthly_limit_usd=200.0)
        usage = await tracker.get_monthly_usage()
        assert isinstance(usage, float)
        assert usage >= 0.0


class TestBudgetMiddleware:
    def setup_method(self) -> None:
        reset_budget_tracker()

    def teardown_method(self) -> None:
        reset_budget_tracker()

    async def test_passes_when_under_budget(self) -> None:
        tracker = BudgetTracker(daily_limit_usd=100.0, monthly_limit_usd=1000.0)
        middleware = BudgetMiddleware(tracker=tracker)

        ctx = GovernanceContext(agent_name="test")
        call_count = 0

        async def call_next(c: GovernanceContext) -> str:
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await middleware.process(ctx, call_next)
        assert result == "ok"
        assert call_count == 1

    async def test_blocks_when_daily_critical(self) -> None:
        """When daily budget is at 100%, calls should be blocked."""
        tracker = BudgetTracker(daily_limit_usd=0.001, monthly_limit_usd=1000.0)
        middleware = BudgetMiddleware(tracker=tracker)

        # Override get_daily_usage to simulate exceeded budget
        original = tracker.get_daily_usage

        async def fake_daily() -> float:
            return 0.002

        tracker.get_daily_usage = fake_daily  # type: ignore[method-assign]

        ctx = GovernanceContext(agent_name="test")

        async def call_next(c: GovernanceContext) -> str:
            return "should_not_reach"

        with pytest.raises(BudgetExceededError) as exc_info:
            await middleware.process(ctx, call_next)

        assert exc_info.value.period == "daily"
        assert exc_info.value.limit_usd == 0.001

        # Restore
        tracker.get_daily_usage = original  # type: ignore[method-assign]

    async def test_bypass_budget_allows_call(self) -> None:
        """Agent with bypass_budget=True should not be blocked."""
        tracker = BudgetTracker(daily_limit_usd=0.001, monthly_limit_usd=1000.0)
        middleware = BudgetMiddleware(tracker=tracker)

        original = tracker.get_daily_usage

        async def fake_daily() -> float:
            return 0.002

        tracker.get_daily_usage = fake_daily  # type: ignore[method-assign]

        ctx = GovernanceContext(agent_name="critical_agent", bypass_budget=True)
        call_count = 0

        async def call_next(c: GovernanceContext) -> str:
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await middleware.process(ctx, call_next)
        assert result == "ok"
        assert call_count == 1

        tracker.get_daily_usage = original  # type: ignore[method-assign]

    async def test_warning_does_not_block(self) -> None:
        """At 80%, warning should fire but call should proceed."""
        tracker = BudgetTracker(daily_limit_usd=10.0, monthly_limit_usd=1000.0)
        middleware = BudgetMiddleware(tracker=tracker)

        # Simulate 85% usage
        original = tracker.get_daily_usage

        async def fake_daily() -> float:
            return 8.5

        tracker.get_daily_usage = fake_daily  # type: ignore[method-assign]

        ctx = GovernanceContext(agent_name="test")
        call_count = 0

        async def call_next(c: GovernanceContext) -> str:
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await middleware.process(ctx, call_next)
        assert result == "ok"
        assert call_count == 1

        tracker.get_daily_usage = original  # type: ignore[method-assign]


class TestBudgetExceededError:
    def test_error_message(self) -> None:
        err = BudgetExceededError("daily", 10.0, 10.5)
        assert "daily" in str(err)
        assert "$10.00" in str(err)
        assert "105.0%" in str(err)

    def test_error_attributes(self) -> None:
        err = BudgetExceededError("monthly", 200.0, 250.0)
        assert err.period == "monthly"
        assert err.limit_usd == 200.0
        assert err.used_usd == 250.0

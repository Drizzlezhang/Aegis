"""End-to-end integration tests for sprint15 paper trading flow.

TODO(sprint16): Rewrite these tests to use BacktestStore instead of PaperBroker.
PaperBroker and PortfolioService were removed in sprint15-hotfix-v0.15.2 (F4: delete paper trading).
"""

import pytest


@pytest.mark.skip(reason="TODO(sprint16): Rewrite with BacktestStore after paper removal")
class TestPaperBrokerE2E:
    """End-to-end: broker -> order lifecycle -> positions -> portfolio."""

    async def test_full_order_lifecycle(self) -> None:
        pass

    async def test_buy_sell_position_netting(self) -> None:
        pass

    async def test_full_sell_closes_position(self) -> None:
        pass

    async def test_portfolio_aggregation(self) -> None:
        pass

    async def test_equity_curve_recording(self) -> None:
        pass

    async def test_reset_clears_all_state(self) -> None:
        pass

    async def test_multi_symbol_positions(self) -> None:
        pass

    async def test_get_orders_filtered(self) -> None:
        pass


@pytest.mark.skip(reason="TODO(sprint16): Rewrite with BacktestStore after paper removal")
class TestEventBusIntegration:
    """Verify EventBus events are published during order lifecycle."""

    async def test_order_submitted_event_published(self) -> None:
        pass

    async def test_order_filled_event_published(self) -> None:
        pass

    async def test_order_cancelled_event_published(self) -> None:
        pass


@pytest.mark.skip(reason="TODO(sprint16): CLI paper commands removed in sprint15-hotfix-v0.15.2")
class TestCLIPaperIntegration:
    """Verify CLI paper commands work end-to-end."""

    def test_paper_help_shows_subcommands(self) -> None:
        pass

    async def test_paper_positions_runs(self) -> None:
        pass

    async def test_paper_portfolio_shows_balance(self) -> None:
        pass

"""End-to-end integration tests for sprint15 paper trading flow."""

import asyncio

import pytest

from src.agents.strategy_exec.brokers.paper import PaperBroker
from src.models.paper import OrderSide, OrderType
from src.services.event_bus import (
    EventBus,
    OrderCancelledEvent,
    OrderFilledEvent,
    OrderRejectedEvent,
    OrderSubmittedEvent,
)
from src.services.portfolio_service import PortfolioService


class TestPaperBrokerE2E:
    """End-to-end: broker → order lifecycle → positions → portfolio."""

    @pytest.fixture
    def broker(self):
        return PaperBroker()

    @pytest.fixture
    def portfolio(self, broker):
        return PortfolioService(broker)

    @pytest.mark.asyncio
    async def test_full_order_lifecycle(self, broker):
        """Place → fill → positions → cancel pending."""
        # Place market buy
        result = await broker.place_order("AAPL", OrderSide.BUY, 10)
        assert result.success
        order_id = result.order_id

        # Verify order filled
        order = await broker.get_order(order_id)
        assert order is not None
        assert order.status.value == "filled"
        assert order.filled_quantity == 10

        # Verify position created
        positions = await broker.get_positions()
        assert len(positions) == 1
        assert positions[0].symbol == "AAPL"
        assert positions[0].quantity == 10

        # Place limit order (won't fill)
        result2 = await broker.place_order(
            "NVDA", OrderSide.BUY, 5, OrderType.LIMIT, limit_price=50.0
        )
        assert result2.success
        pending_id = result2.order_id

        # Cancel pending order
        cancelled = await broker.cancel_order(pending_id)
        assert cancelled is True

        # Verify cancelled
        cancelled_order = await broker.get_order(pending_id)
        assert cancelled_order.status.value == "cancelled"

    @pytest.mark.asyncio
    async def test_buy_sell_position_netting(self, broker):
        """Buy then sell should net positions correctly."""
        await broker.place_order("AAPL", OrderSide.BUY, 10)
        await broker.place_order("AAPL", OrderSide.SELL, 3)

        positions = await broker.get_positions()
        assert len(positions) == 1
        assert positions[0].quantity == 7

    @pytest.mark.asyncio
    async def test_full_sell_closes_position(self, broker):
        """Selling all shares removes position."""
        await broker.place_order("AAPL", OrderSide.BUY, 5)
        await broker.place_order("AAPL", OrderSide.SELL, 5)

        positions = await broker.get_positions()
        assert len(positions) == 0

    @pytest.mark.asyncio
    async def test_portfolio_aggregation(self, broker, portfolio):
        """Portfolio service aggregates broker state correctly."""
        await broker.place_order("AAPL", OrderSide.BUY, 10)

        snapshot = await portfolio.get_snapshot()
        assert snapshot.position_count == 1 if hasattr(snapshot, 'position_count') else len(snapshot.positions) == 1
        assert snapshot.cash < 100000.0

    @pytest.mark.asyncio
    async def test_equity_curve_recording(self, broker, portfolio):
        """Portfolio service records equity curve snapshots."""
        await broker.place_order("AAPL", OrderSide.BUY, 10)

        await portfolio.record_snapshot()
        await portfolio.record_snapshot()

        curve = portfolio.get_equity_curve()
        assert len(curve) == 2

        stats = portfolio.get_stats()
        assert stats["total_snapshots"] == 2

    @pytest.mark.asyncio
    async def test_reset_clears_all_state(self, broker, portfolio):
        """Reset clears orders, positions, and equity curve."""
        await broker.place_order("AAPL", OrderSide.BUY, 10)
        await portfolio.record_snapshot()

        broker.reset()
        portfolio.reset()

        orders = await broker.get_orders()
        positions = await broker.get_positions()
        curve = portfolio.get_equity_curve()

        assert len(orders) == 0
        assert len(positions) == 0
        assert len(curve) == 0

    @pytest.mark.asyncio
    async def test_multi_symbol_positions(self, broker):
        """Multiple symbols create separate positions."""
        await broker.place_order("AAPL", OrderSide.BUY, 10)
        await broker.place_order("NVDA", OrderSide.BUY, 5)
        await broker.place_order("MSFT", OrderSide.BUY, 3)

        positions = await broker.get_positions()
        assert len(positions) == 3

        symbols = {p.symbol for p in positions}
        assert symbols == {"AAPL", "NVDA", "MSFT"}

    @pytest.mark.asyncio
    async def test_get_orders_filtered(self, broker):
        """Orders can be filtered by status."""
        await broker.place_order("AAPL", OrderSide.BUY, 10)  # filled
        await broker.place_order("NVDA", OrderSide.BUY, 5, OrderType.LIMIT, limit_price=50.0)  # pending

        filled = await broker.get_orders(status="filled")
        pending = await broker.get_orders(status="pending")

        assert len(filled) == 1
        assert len(pending) == 1
        assert filled[0].symbol == "AAPL"
        assert pending[0].symbol == "NVDA"


class TestEventBusIntegration:
    """Verify EventBus events are published during order lifecycle."""

    @pytest.mark.asyncio
    async def test_order_submitted_event_published(self):
        """OrderSubmittedEvent is published when order is placed."""
        received: list[OrderSubmittedEvent] = []
        bus = EventBus()
        bus.subscribe("OrderSubmittedEvent", lambda e: received.append(e))
        await bus.start()

        broker = PaperBroker(event_bus=bus)
        await broker.place_order("AAPL", OrderSide.BUY, 10)

        # Allow dispatch loop to process
        await asyncio.sleep(0.1)
        await bus.stop()

        assert len(received) == 1
        assert received[0].symbol == "AAPL"
        assert received[0].quantity == 10

    @pytest.mark.asyncio
    async def test_order_filled_event_published(self):
        """OrderFilledEvent is published when market order fills."""
        received: list[OrderFilledEvent] = []
        bus = EventBus()
        bus.subscribe("OrderFilledEvent", lambda e: received.append(e))
        await bus.start()

        broker = PaperBroker(event_bus=bus)
        await broker.place_order("AAPL", OrderSide.BUY, 10)

        await asyncio.sleep(0.1)
        await bus.stop()

        assert len(received) == 1
        assert received[0].symbol == "AAPL"
        assert received[0].filled_quantity == 10

    @pytest.mark.asyncio
    async def test_order_cancelled_event_published(self):
        """OrderCancelledEvent is published when order is cancelled."""
        received: list[OrderCancelledEvent] = []
        bus = EventBus()
        bus.subscribe("OrderCancelledEvent", lambda e: received.append(e))
        await bus.start()

        broker = PaperBroker(event_bus=bus)
        result = await broker.place_order(
            "NVDA", OrderSide.BUY, 5, OrderType.LIMIT, limit_price=50.0
        )
        await broker.cancel_order(result.order_id)

        await asyncio.sleep(0.1)
        await bus.stop()

        assert len(received) == 1
        assert received[0].symbol == "NVDA"


class TestCLIPaperIntegration:
    """Verify CLI paper commands work end-to-end."""

    def test_paper_help_shows_subcommands(self, monkeypatch, capsys):
        """`aegis paper --help` shows all subcommands."""
        import sys
        from src import cli

        monkeypatch.setattr(sys, "argv", ["aegis", "paper", "--help"])
        with pytest.raises(SystemExit):
            cli.main()
        captured = capsys.readouterr()
        assert "positions" in captured.out
        assert "orders" in captured.out
        assert "portfolio" in captured.out
        assert "reset" in captured.out

    @pytest.mark.asyncio
    async def test_paper_positions_runs(self, monkeypatch, capsys):
        """CLI paper positions runs without error."""
        import sys
        from src import cli

        monkeypatch.setattr(sys, "argv", ["aegis", "paper", "positions"])
        await cli.main_async()
        captured = capsys.readouterr()
        assert "No open positions" in captured.out

    @pytest.mark.asyncio
    async def test_paper_portfolio_shows_balance(self, monkeypatch, capsys):
        """CLI portfolio shows cash and equity."""
        import sys
        from src import cli

        monkeypatch.setattr(sys, "argv", ["aegis", "paper", "portfolio"])
        await cli.main_async()
        captured = capsys.readouterr()
        assert "Cash:" in captured.out
        assert "Equity:" in captured.out

"""Broker abstraction layer for strategy execution.

allowlist: paper-sandbox / DSS-internal — NOT a real broker adapter.
This directory is excluded from the Sprint 16 constitution grep guard.
"""

from abc import ABC, abstractmethod

from src.models.paper import (
    AccountSnapshot,
    Order,
    OrderResult,
    OrderSide,
    OrderType,
    PositionSnapshot,
)


class BrokerBase(ABC):
    """Abstract interface for order execution brokers.

    Implementations: PaperBroker (simulated), LiveBroker (real exchange).
    """

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        limit_price: float | None = None,
        stop_price: float | None = None,
    ) -> OrderResult:
        """Place a new order.

        Args:
            symbol: Trading symbol (e.g. "AAPL").
            side: Buy or sell.
            quantity: Number of shares/contracts.
            order_type: Market, limit, or stop.
            limit_price: Required for limit orders.
            stop_price: Required for stop orders.

        Returns:
            OrderResult with success status and order ID.
        """
        ...

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending or submitted order.

        Returns:
            True if the order was found and cancelled.
        """
        ...

    @abstractmethod
    async def get_order(self, order_id: str) -> Order | None:
        """Get an order by ID.

        Returns:
            The order if found, None otherwise.
        """
        ...

    @abstractmethod
    async def get_orders(self, symbol: str | None = None, status: str | None = None) -> list[Order]:
        """Get all orders, optionally filtered by symbol or status.

        Args:
            symbol: Filter by symbol.
            status: Filter by order status (e.g. "filled", "pending").

        Returns:
            List of matching orders.
        """
        ...

    @abstractmethod
    async def get_positions(self) -> list[PositionSnapshot]:
        """Get current positions.

        Returns:
            List of position snapshots.
        """
        ...

    @abstractmethod
    async def get_balance(self) -> AccountSnapshot:
        """Get current account balance.

        Returns:
            Account snapshot with cash, equity, buying power, and positions.
        """
        ...

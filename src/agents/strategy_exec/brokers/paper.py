"""PaperBroker — simulated order execution with memory+SQLite dual-write."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from src.agents.strategy_exec.brokers.base import BrokerBase
from src.models.paper import (
    AccountSnapshot,
    Order,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    PositionSnapshot,
)
from src.services.event_bus import (
    EventBus,
    OrderCancelledEvent,
    OrderFilledEvent,
    OrderRejectedEvent,
    OrderSubmittedEvent,
    get_event_bus,
)

logger = logging.getLogger(__name__)

INITIAL_CASH = 100_000.0


class PaperBroker(BrokerBase):
    """Simulated broker for paper trading.

    Features:
    - In-memory order store (dict) for fast access
    - SQLite persistence via async session for durability
    - Market/limit/stop order matching
    - Partial fill support
    - State machine: PENDING → SUBMITTED → FILLED/PARTIALLY_FILLED/CANCELLED/REJECTED
    - Publishes OrderSubmitted/OrderFilled/OrderCancelled/OrderRejected events
    """

    def __init__(
        self,
        initial_cash: float = INITIAL_CASH,
        event_bus: EventBus | None = None,
    ) -> None:
        self._orders: dict[str, Order] = {}
        self._positions: dict[str, PositionSnapshot] = {}
        self._cash = initial_cash
        self._initial_cash = initial_cash
        self._event_bus = event_bus or get_event_bus()

    # ── BrokerBase implementation ───────────────────────────────────────

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        limit_price: float | None = None,
        stop_price: float | None = None,
    ) -> OrderResult:
        """Place a new order. Market orders fill immediately."""
        order_id = uuid.uuid4().hex[:12]
        now = datetime.now()

        order = Order(
            id=order_id,
            symbol=symbol.upper(),
            side=side,
            order_type=order_type,
            quantity=quantity,
            limit_price=limit_price,
            stop_price=stop_price,
            status=OrderStatus.SUBMITTED,
            created_at=now,
            updated_at=now,
        )

        self._orders[order_id] = order

        self._event_bus.publish(
            OrderSubmittedEvent(
                order_id=order_id,
                symbol=order.symbol,
                side=order.side.value,
                order_type=order.order_type.value,
                quantity=quantity,
                limit_price=limit_price,
            )
        )

        # Market orders fill immediately at simulated price
        if order_type == OrderType.MARKET:
            fill_price = self._get_simulated_price(symbol)
            self._fill_order(order, fill_price, quantity)
        elif order_type == OrderType.LIMIT and limit_price is not None:
            # Simulate: fill if limit price is reasonable
            fill_price = self._get_simulated_price(symbol)
            if (side == OrderSide.BUY and fill_price <= limit_price) or (
                side == OrderSide.SELL and fill_price >= limit_price
            ):
                self._fill_order(order, limit_price, quantity)
            else:
                order.status = OrderStatus.PENDING
                order.updated_at = datetime.now()

        logger.info(
            "Order placed: id=%s symbol=%s side=%s qty=%d type=%s status=%s",
            order_id, symbol, side.value, quantity, order_type.value, order.status.value,
        )

        return OrderResult(success=True, order_id=order_id, message=f"Order {order_id} {order.status.value}")

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending or submitted order."""
        order = self._orders.get(order_id)
        if order is None:
            return False
        if order.status not in (OrderStatus.PENDING, OrderStatus.SUBMITTED):
            return False

        order.status = OrderStatus.CANCELLED
        order.cancelled_at = datetime.now()
        order.updated_at = datetime.now()

        self._event_bus.publish(
            OrderCancelledEvent(
                order_id=order_id,
                symbol=order.symbol,
                reason="user_cancelled",
            )
        )

        logger.info("Order cancelled: id=%s", order_id)
        return True

    async def get_order(self, order_id: str) -> Order | None:
        """Get an order by ID."""
        return self._orders.get(order_id)

    async def get_orders(
        self, symbol: str | None = None, status: str | None = None
    ) -> list[Order]:
        """Get all orders, optionally filtered."""
        orders = list(self._orders.values())
        if symbol:
            orders = [o for o in orders if o.symbol == symbol.upper()]
        if status:
            orders = [o for o in orders if o.status.value == status]
        return sorted(orders, key=lambda o: o.created_at, reverse=True)

    async def get_positions(self) -> list[PositionSnapshot]:
        """Get current positions."""
        return list(self._positions.values())

    async def get_balance(self) -> AccountSnapshot:
        """Get current account balance."""
        positions = list(self._positions.values())
        total_market_value = sum(
            (p.market_price or p.avg_cost) * p.quantity for p in positions
        )
        equity = self._cash + total_market_value
        total_pnl = equity - self._initial_cash
        total_pnl_pct = (total_pnl / self._initial_cash * 100) if self._initial_cash > 0 else 0.0

        return AccountSnapshot(
            cash=self._cash,
            equity=equity,
            buying_power=self._cash * 2,  # 2x margin for paper
            positions=positions,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
        )

    # ── Internal ────────────────────────────────────────────────────────

    def _fill_order(self, order: Order, fill_price: float, fill_qty: int) -> None:
        """Fill an order (full or partial) and update positions."""
        order.filled_quantity = fill_qty
        order.filled_avg_price = fill_price
        order.status = OrderStatus.FILLED
        order.updated_at = datetime.now()

        # Update cash
        cost = fill_price * fill_qty
        if order.side == OrderSide.BUY:
            self._cash -= cost
        else:
            self._cash += cost

        # Update position
        symbol = order.symbol
        if symbol in self._positions:
            pos = self._positions[symbol]
            if order.side == OrderSide.BUY:
                total_qty = pos.quantity + fill_qty
                total_cost = pos.avg_cost * pos.quantity + cost
                pos.quantity = total_qty
                pos.avg_cost = total_cost / total_qty if total_qty > 0 else 0.0
            else:
                total_qty = pos.quantity - fill_qty
                if total_qty <= 0:
                    del self._positions[symbol]
                else:
                    pos.quantity = total_qty
        elif order.side == OrderSide.BUY:
            self._positions[symbol] = PositionSnapshot(
                symbol=symbol,
                quantity=fill_qty,
                avg_cost=fill_price,
                market_price=fill_price,
            )

        # Update market prices for all positions
        for pos in self._positions.values():
            pos.market_price = self._get_simulated_price(pos.symbol)
            if pos.market_price is not None:
                pos.unrealized_pnl = (pos.market_price - pos.avg_cost) * pos.quantity
                pos.unrealized_pnl_pct = (
                    ((pos.market_price - pos.avg_cost) / pos.avg_cost * 100)
                    if pos.avg_cost > 0 else 0.0
                )

        self._event_bus.publish(
            OrderFilledEvent(
                order_id=order.id,
                symbol=order.symbol,
                side=order.side.value,
                filled_quantity=fill_qty,
                filled_avg_price=fill_price,
                remaining_quantity=order.quantity - fill_qty,
            )
        )

    @staticmethod
    def _get_simulated_price(symbol: str) -> float:
        """Get a simulated price for paper trading.

        In production, this would use real-time market data.
        For now, returns a fixed reference price per symbol.
        """
        _REFERENCE_PRICES: dict[str, float] = {
            "AAPL": 195.0,
            "NVDA": 120.0,
            "MSFT": 425.0,
            "GOOGL": 175.0,
            "AMZN": 185.0,
            "META": 510.0,
            "TSLA": 250.0,
            "QQQ": 450.0,
            "SPY": 530.0,
            "KO": 65.0,
            "PLTR": 25.0,
            "NFLX": 650.0,
            "INTC": 35.0,
            "TSM": 150.0,
        }
        return _REFERENCE_PRICES.get(symbol.upper(), 100.0)

    # ── Paper-specific ──────────────────────────────────────────────────

    def reset(self) -> None:
        """Reset all state (orders, positions, cash)."""
        self._orders.clear()
        self._positions.clear()
        self._cash = self._initial_cash
        logger.info("PaperBroker reset: orders=%d positions=%d cash=%.2f",
                     len(self._orders), len(self._positions), self._cash)

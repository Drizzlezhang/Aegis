"""PaperBroker — simulated order execution with memory+SQLite dual-write."""

from __future__ import annotations

import asyncio
import logging
import random
import uuid
from datetime import datetime
from pathlib import Path

import aiosqlite

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
DEFAULT_DB_PATH = "~/.aegis-trader/paper_state.sqlite"

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


class PaperBroker(BrokerBase):
    """Simulated broker for paper trading.

    Features:
    - In-memory order store (dict) for fast access
    - SQLite persistence via aiosqlite for durability
    - Market/limit/stop order matching
    - Partial fill support with simulated liquidity
    - STOP order book with price-triggered activation
    - Price cache with configurable noise
    - State machine: PENDING → SUBMITTED → FILLED/PARTIALLY_FILLED/CANCELLED/REJECTED
    - Publishes OrderSubmitted/OrderFilled/OrderCancelled/OrderRejected events
    """

    def __init__(
        self,
        initial_cash: float = INITIAL_CASH,
        event_bus: EventBus | None = None,
        db_path: str = DEFAULT_DB_PATH,
    ) -> None:
        self._orders: dict[str, Order] = {}
        self._positions: dict[str, PositionSnapshot] = {}
        self._stop_book: dict[str, Order] = {}
        self._cash = initial_cash
        self._initial_cash = initial_cash
        self._event_bus = event_bus or get_event_bus()
        self._db_path = Path(db_path).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db: aiosqlite.Connection | None = None
        self._db_lock = asyncio.Lock()
        self._price_book: dict[str, float] = {}
        self._unknown_symbol_warned: set[str] = set()
        self._initialized = False

    # ── Database ────────────────────────────────────────────────────────

    async def _get_db(self) -> aiosqlite.Connection:
        if self._db is None:
            self._db = await aiosqlite.connect(str(self._db_path))
            self._db.row_factory = aiosqlite.Row
            await self._db.execute("PRAGMA journal_mode=WAL")
            await self._db.execute("PRAGMA foreign_keys=ON")
        return self._db

    async def _init_db(self) -> None:
        db = await self._get_db()
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                order_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                filled_quantity INTEGER NOT NULL DEFAULT 0,
                limit_price REAL,
                stop_price REAL,
                filled_avg_price REAL,
                status TEXT NOT NULL,
                rejection_reason TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                cancelled_at TEXT
            );
            CREATE TABLE IF NOT EXISTS positions (
                symbol TEXT PRIMARY KEY,
                quantity INTEGER NOT NULL,
                avg_cost REAL NOT NULL,
                market_price REAL,
                unrealized_pnl REAL,
                unrealized_pnl_pct REAL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS equity_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                cash REAL NOT NULL,
                equity REAL NOT NULL,
                buying_power REAL NOT NULL,
                total_pnl REAL NOT NULL,
                total_pnl_pct REAL NOT NULL,
                position_count INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS price_cache (
                symbol TEXT PRIMARY KEY,
                price REAL NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        await db.commit()

    async def _load_state(self) -> None:
        """Reload orders, positions, and cash from SQLite."""
        db = await self._get_db()
        await self._init_db()

        # Load cash
        cursor = await db.execute("SELECT value FROM state WHERE key = 'cash'")
        row = await cursor.fetchone()
        if row:
            self._cash = float(row[0])

        # Load orders
        cursor = await db.execute("SELECT * FROM orders")
        rows = await cursor.fetchall()
        for row in rows:
            order = Order(
                id=row["order_id"],
                symbol=row["symbol"],
                side=OrderSide(row["side"]),
                order_type=OrderType(row["order_type"]),
                quantity=row["quantity"],
                filled_quantity=row["filled_quantity"],
                limit_price=row["limit_price"],
                stop_price=row["stop_price"],
                filled_avg_price=row["filled_avg_price"],
                status=OrderStatus(row["status"]),
                rejection_reason=row["rejection_reason"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                cancelled_at=datetime.fromisoformat(row["cancelled_at"]) if row["cancelled_at"] else None,
            )
            self._orders[order.id] = order
            if order.order_type == OrderType.STOP and order.status in (
                OrderStatus.PENDING, OrderStatus.SUBMITTED,
            ):
                self._stop_book[order.id] = order

        # Load positions
        cursor = await db.execute("SELECT * FROM positions")
        rows = await cursor.fetchall()
        for row in rows:
            pos = PositionSnapshot(
                symbol=row["symbol"],
                quantity=row["quantity"],
                avg_cost=row["avg_cost"],
                market_price=row["market_price"],
                unrealized_pnl=row["unrealized_pnl"],
                unrealized_pnl_pct=row["unrealized_pnl_pct"],
            )
            self._positions[pos.symbol] = pos

        # Backfill _price_book from price_cache table
        cursor = await db.execute("SELECT symbol, price FROM price_cache")
        rows = await cursor.fetchall()
        for row in rows:
            self._price_book[row["symbol"]] = float(row["price"])

        logger.info(
            "PaperBroker loaded from %s: orders=%d positions=%d cash=%.2f prices=%d",
            self._db_path, len(self._orders), len(self._positions), self._cash,
            len(self._price_book),
        )

    async def _ensure_initialized(self) -> None:
        if not self._initialized:
            async with self._db_lock:
                if not self._initialized:
                    await self._init_db()
                    await self._load_state()
                    self._initialized = True

    async def _save_order(self, order: Order) -> None:
        db = await self._get_db()
        await db.execute(
            """INSERT OR REPLACE INTO orders
               (order_id, symbol, side, order_type, quantity, filled_quantity,
                limit_price, stop_price, filled_avg_price, status, rejection_reason,
                created_at, updated_at, cancelled_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                order.id, order.symbol, order.side.value, order.order_type.value,
                order.quantity, order.filled_quantity,
                order.limit_price, order.stop_price, order.filled_avg_price,
                order.status.value, order.rejection_reason,
                order.created_at.isoformat(), order.updated_at.isoformat(),
                order.cancelled_at.isoformat() if order.cancelled_at else None,
            ),
        )
        await db.commit()

    async def _save_position(self, symbol: str, pos: PositionSnapshot | None) -> None:
        db = await self._get_db()
        if pos is None:
            await db.execute("DELETE FROM positions WHERE symbol = ?", (symbol,))
        else:
            await db.execute(
                """INSERT OR REPLACE INTO positions
                   (symbol, quantity, avg_cost, market_price, unrealized_pnl,
                    unrealized_pnl_pct, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    pos.symbol, pos.quantity, pos.avg_cost,
                    pos.market_price, pos.unrealized_pnl, pos.unrealized_pnl_pct,
                    datetime.now().isoformat(),
                ),
            )
        await db.commit()

    async def _save_cash(self) -> None:
        db = await self._get_db()
        await db.execute(
            "INSERT OR REPLACE INTO state (key, value) VALUES ('cash', ?)",
            (str(self._cash),),
        )
        await db.commit()

    async def _save_price(self, symbol: str, price: float) -> None:
        db = await self._get_db()
        await db.execute(
            "INSERT OR REPLACE INTO price_cache (symbol, price, updated_at) VALUES (?, ?, ?)",
            (symbol.upper(), price, datetime.now().isoformat()),
        )
        await db.commit()

    async def _save_equity_snapshot(self, snapshot: AccountSnapshot) -> None:
        db = await self._get_db()
        await db.execute(
            """INSERT INTO equity_snapshots
               (timestamp, cash, equity, buying_power, total_pnl, total_pnl_pct, position_count)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now().isoformat(),
                snapshot.cash, snapshot.equity, snapshot.buying_power,
                snapshot.total_pnl, snapshot.total_pnl_pct,
                len(snapshot.positions),
            ),
        )
        await db.commit()

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
        """Place a new order. Market orders fill immediately (possibly partial)."""
        await self._ensure_initialized()

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
        await self._save_order(order)

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

        if order_type == OrderType.MARKET:
            fill_price = self._get_simulated_price(symbol)
            fill_qty = self._get_simulated_liquidity(symbol, quantity)
            self._fill_order(order, fill_price, fill_qty)
            await self._save_order(order)
        elif order_type == OrderType.LIMIT and limit_price is not None:
            fill_price = self._get_simulated_price(symbol)
            if (side == OrderSide.BUY and fill_price <= limit_price) or (
                side == OrderSide.SELL and fill_price >= limit_price
            ):
                fill_qty = self._get_simulated_liquidity(symbol, quantity)
                self._fill_order(order, limit_price, fill_qty)
                await self._save_order(order)
            else:
                order.status = OrderStatus.PENDING
                order.updated_at = datetime.now()
                await self._save_order(order)
        elif order_type == OrderType.STOP and stop_price is not None:
            order.status = OrderStatus.PENDING
            order.updated_at = datetime.now()
            self._stop_book[order_id] = order
            await self._save_order(order)

        logger.info(
            "Order placed: id=%s symbol=%s side=%s qty=%d type=%s status=%s",
            order_id, symbol, side.value, quantity, order_type.value, order.status.value,
        )

        return OrderResult(
            success=True, order_id=order_id, message=f"Order {order_id} {order.status.value}",
        )

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending or submitted order."""
        await self._ensure_initialized()

        order = self._orders.get(order_id)
        if order is None:
            return False
        if order.status not in (OrderStatus.PENDING, OrderStatus.SUBMITTED):
            return False

        order.status = OrderStatus.CANCELLED
        order.cancelled_at = datetime.now()
        order.updated_at = datetime.now()
        self._stop_book.pop(order_id, None)
        await self._save_order(order)

        self._event_bus.publish(
            OrderCancelledEvent(
                order_id=order_id,
                symbol=order.symbol,
                reason="user_cancelled",
            )
        )

        logger.info("Order cancelled: id=%s", order_id)
        return True

    async def reject_order(self, order_id: str, reason: str = "rejected") -> bool:
        """Reject an order (e.g., insufficient funds, invalid symbol)."""
        await self._ensure_initialized()

        order = self._orders.get(order_id)
        if order is None:
            return False
        if order.status not in (OrderStatus.PENDING, OrderStatus.SUBMITTED):
            return False

        order.status = OrderStatus.REJECTED
        order.rejection_reason = reason
        order.updated_at = datetime.now()
        self._stop_book.pop(order_id, None)
        await self._save_order(order)

        self._event_bus.publish(
            OrderRejectedEvent(
                order_id=order_id,
                symbol=order.symbol,
                reason=reason,
            )
        )

        logger.info("Order rejected: id=%s reason=%s", order_id, reason)
        return True

    async def get_order(self, order_id: str) -> Order | None:
        """Get an order by ID."""
        await self._ensure_initialized()
        return self._orders.get(order_id)

    async def get_orders(
        self, symbol: str | None = None, status: str | None = None,
    ) -> list[Order]:
        """Get all orders, optionally filtered."""
        await self._ensure_initialized()
        orders = list(self._orders.values())
        if symbol:
            orders = [o for o in orders if o.symbol == symbol.upper()]
        if status:
            orders = [o for o in orders if o.status.value == status]
        return sorted(orders, key=lambda o: o.created_at, reverse=True)

    async def get_positions(self) -> list[PositionSnapshot]:
        """Get current positions."""
        await self._ensure_initialized()
        return list(self._positions.values())

    async def get_balance(self) -> AccountSnapshot:
        """Get current account balance."""
        await self._ensure_initialized()
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

    # ── STOP order checking ─────────────────────────────────────────────

    async def check_stop_orders(self) -> list[str]:
        """Check all pending STOP orders against current prices.

        If a STOP order's trigger price is reached, convert to market and fill.

        Returns:
            List of triggered order IDs.
        """
        await self._ensure_initialized()
        triggered: list[str] = []

        for order_id, order in list(self._stop_book.items()):
            if order.stop_price is None:
                continue
            current_price = self._get_simulated_price(order.symbol)
            triggered_flag = False

            if order.side == OrderSide.BUY and current_price >= order.stop_price:
                triggered_flag = True
            elif order.side == OrderSide.SELL and current_price <= order.stop_price:
                triggered_flag = True

            if triggered_flag:
                fill_qty = self._get_simulated_liquidity(order.symbol, order.quantity)
                self._fill_order(order, current_price, fill_qty)
                await self._save_order(order)
                self._stop_book.pop(order_id, None)
                triggered.append(order_id)
                logger.info(
                    "STOP order triggered: id=%s symbol=%s stop=%.2f current=%.2f",
                    order_id, order.symbol, order.stop_price, current_price,
                )

        return triggered

    # ── Price book ──────────────────────────────────────────────────────

    async def update_price(self, symbol: str, price: float) -> None:
        """Update the cached price for a symbol (e.g., from DataService).

        Dual-writes to in-memory _price_book and SQLite price_cache.
        """
        await self._ensure_initialized()
        key = symbol.upper()
        self._price_book[key] = price
        await self._save_price(symbol, price)

    def _get_simulated_price(self, symbol: str) -> float:
        """Get a simulated price with noise.

        Priority: _price_book (from update_price) → _REFERENCE_PRICES → $100 fallback.
        Adds ±2% random noise for realistic simulation.
        Unknown symbols log a WARN once per symbol.
        """
        key = symbol.upper()
        if key in self._price_book:
            base = self._price_book[key]
        elif key in _REFERENCE_PRICES:
            base = _REFERENCE_PRICES[key]
        else:
            base = 100.0
            if key not in self._unknown_symbol_warned:
                self._unknown_symbol_warned.add(key)
                logger.warning(
                    "No price data for symbol %s; using fallback $100. "
                    "Call update_price() to set a real price.",
                    key,
                )
        noise = random.uniform(-0.02, 0.02)
        return round(base * (1 + noise), 2)

    async def get_cached_price(self, symbol: str) -> float | None:
        """Get the cached price from SQLite price_cache table."""
        await self._ensure_initialized()
        db = await self._get_db()
        cursor = await db.execute(
            "SELECT price FROM price_cache WHERE symbol = ?", (symbol.upper(),),
        )
        row = await cursor.fetchone()
        return float(row[0]) if row else None

    # ── Internal ────────────────────────────────────────────────────────

    @staticmethod
    def _get_simulated_liquidity(symbol: str, requested: int) -> int:
        """Simulate available liquidity for partial fills.

        Returns a random fill quantity between 1 and requested.
        70% chance of full fill, 30% chance of partial (50-99%).
        """
        if requested <= 1:
            return requested
        if random.random() < 0.7:
            return requested
        return max(1, int(requested * random.uniform(0.5, 0.99)))

    def _fill_order(self, order: Order, fill_price: float, fill_qty: int) -> None:
        """Fill an order (full or partial) and update positions."""
        if fill_qty <= 0:
            return

        actual_fill = min(fill_qty, order.quantity - order.filled_quantity)
        if actual_fill <= 0:
            return

        order.filled_quantity += actual_fill
        order.filled_avg_price = fill_price
        order.updated_at = datetime.now()

        remaining = order.quantity - order.filled_quantity
        if remaining <= 0:
            order.status = OrderStatus.FILLED
        else:
            order.status = OrderStatus.PARTIALLY_FILLED

        # Update cash
        cost = fill_price * actual_fill
        if order.side == OrderSide.BUY:
            self._cash -= cost
        else:
            self._cash += cost

        # Update position
        symbol = order.symbol
        if symbol in self._positions:
            pos = self._positions[symbol]
            if order.side == OrderSide.BUY:
                total_qty = pos.quantity + actual_fill
                total_cost = pos.avg_cost * pos.quantity + cost
                pos.quantity = total_qty
                pos.avg_cost = total_cost / total_qty if total_qty > 0 else 0.0
            else:
                total_qty = pos.quantity - actual_fill
                if total_qty <= 0:
                    del self._positions[symbol]
                    asyncio.ensure_future(self._save_position(symbol, None))
                    symbol = ""  # prevent double-save below
                else:
                    pos.quantity = total_qty
        elif order.side == OrderSide.BUY:
            self._positions[symbol] = PositionSnapshot(
                symbol=symbol,
                quantity=actual_fill,
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

        # Persist position if still exists
        if symbol and symbol in self._positions:
            asyncio.ensure_future(self._save_position(symbol, self._positions[symbol]))
        asyncio.ensure_future(self._save_cash())

        self._event_bus.publish(
            OrderFilledEvent(
                order_id=order.id,
                symbol=order.symbol,
                side=order.side.value,
                filled_quantity=actual_fill,
                filled_avg_price=fill_price,
                remaining_quantity=remaining,
            )
        )

    # ── Paper-specific ──────────────────────────────────────────────────

    async def reset(self) -> None:
        """Reset all state (orders, positions, cash, DB tables)."""
        self._orders.clear()
        self._positions.clear()
        self._stop_book.clear()
        self._price_book.clear()
        self._unknown_symbol_warned.clear()
        self._cash = self._initial_cash

        db = await self._get_db()
        await self._init_db()
        await db.executescript("""
            DELETE FROM orders;
            DELETE FROM positions;
            DELETE FROM equity_snapshots;
            DELETE FROM price_cache;
            DELETE FROM state;
        """)
        await db.commit()

        logger.info(
            "PaperBroker reset: orders=%d positions=%d cash=%.2f",
            len(self._orders), len(self._positions), self._cash,
        )

    async def close(self) -> None:
        """Close the database connection."""
        if self._db is not None:
            await self._db.close()
            self._db = None
            self._initialized = False

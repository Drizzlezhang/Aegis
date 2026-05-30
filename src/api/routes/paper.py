"""Paper trading API routes."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.agents.strategy_exec.brokers.paper import PaperBroker
from src.models.paper import OrderSide, OrderType
from src.services.portfolio_service import PortfolioService

router = APIRouter()


# ── Response Models ──────────────────────────────────────────────────────────


class OrderItem(BaseModel):
    id: str
    symbol: str
    side: str
    orderType: str
    quantity: int
    limitPrice: float | None = None
    stopPrice: float | None = None
    status: str
    filledQuantity: int
    filledAvgPrice: float | None = None
    createdAt: str
    updatedAt: str
    cancelledAt: str | None = None


class OrdersResponse(BaseModel):
    orders: list[OrderItem]
    total: int


class PositionItem(BaseModel):
    symbol: str
    quantity: int
    avgCost: float
    marketPrice: float | None = None
    unrealizedPnl: float | None = None
    unrealizedPnlPct: float | None = None


class PositionsResponse(BaseModel):
    positions: list[PositionItem]
    total: int


class PortfolioResponse(BaseModel):
    cash: float
    equity: float
    buyingPower: float
    totalPnl: float
    totalPnlPct: float
    positionCount: int
    equityCurveSnapshots: int
    totalReturnPct: float
    maxDrawdownPct: float
    maxEquity: float
    minEquity: float


class PlaceOrderRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    side: str = Field(..., pattern="^(buy|sell)$")
    orderType: str = Field(default="market", pattern="^(market|limit|stop)$")
    quantity: int = Field(..., gt=0)
    limitPrice: float | None = None
    stopPrice: float | None = None


class PlaceOrderResponse(BaseModel):
    success: bool
    orderId: str
    message: str


class CancelOrderResponse(BaseModel):
    success: bool
    orderId: str
    message: str


class ResetResponse(BaseModel):
    success: bool
    message: str


# ── Service ──────────────────────────────────────────────────────────────────

_broker: PaperBroker | None = None
_portfolio: PortfolioService | None = None


def _get_broker() -> PaperBroker:
    global _broker
    if _broker is None:
        _broker = PaperBroker()
    return _broker


def _get_portfolio() -> PortfolioService:
    global _portfolio
    if _portfolio is None:
        _portfolio = PortfolioService(_get_broker())
    return _portfolio


class _PaperRouteService:
    def __init__(self) -> None:
        self._broker = _get_broker()
        self._portfolio = _get_portfolio()

    async def get_orders(self, status: str | None = None) -> dict:
        orders = await self._broker.get_orders(status=status)
        return {
            "orders": [self._to_order_item(o) for o in orders],
            "total": len(orders),
        }

    async def get_positions(self) -> dict:
        positions = await self._broker.get_positions()
        return {
            "positions": [self._to_position_item(p) for p in positions],
            "total": len(positions),
        }

    async def get_portfolio(self) -> dict:
        snapshot = await self._portfolio.get_snapshot()
        stats = self._portfolio.get_stats()
        return {
            "cash": snapshot.cash,
            "equity": snapshot.equity,
            "buyingPower": snapshot.buying_power,
            "totalPnl": snapshot.total_pnl,
            "totalPnlPct": snapshot.total_pnl_pct,
            "positionCount": len(snapshot.positions),
            "equityCurveSnapshots": stats["total_snapshots"],
            "totalReturnPct": stats["total_return_pct"],
            "maxDrawdownPct": stats["max_drawdown_pct"],
            "maxEquity": stats["max_equity"],
            "minEquity": stats["min_equity"],
        }

    async def place_order(self, req: PlaceOrderRequest) -> dict:
        side = OrderSide.BUY if req.side == "buy" else OrderSide.SELL
        order_type = OrderType(req.orderType)
        result = await self._broker.place_order(
            symbol=req.symbol,
            side=side,
            quantity=req.quantity,
            order_type=order_type,
            limit_price=req.limitPrice,
            stop_price=req.stopPrice,
        )
        return {"success": result.success, "orderId": result.order_id, "message": result.message}

    async def cancel_order(self, order_id: str) -> dict:
        cancelled = await self._broker.cancel_order(order_id)
        if not cancelled:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found or cannot be cancelled")
        return {"success": True, "orderId": order_id, "message": f"Order {order_id} cancelled"}

    async def reset(self) -> dict:
        self._broker.reset()
        self._portfolio.reset()
        return {"success": True, "message": "Paper trading state reset"}

    @staticmethod
    def _to_order_item(order) -> dict:
        return {
            "id": order.id,
            "symbol": order.symbol,
            "side": order.side.value,
            "orderType": order.order_type.value,
            "quantity": order.quantity,
            "limitPrice": order.limit_price,
            "stopPrice": order.stop_price,
            "status": order.status.value,
            "filledQuantity": order.filled_quantity,
            "filledAvgPrice": order.filled_avg_price,
            "createdAt": order.created_at.isoformat(),
            "updatedAt": order.updated_at.isoformat(),
            "cancelledAt": order.cancelled_at.isoformat() if order.cancelled_at else None,
        }

    @staticmethod
    def _to_position_item(position) -> dict:
        return {
            "symbol": position.symbol,
            "quantity": position.quantity,
            "avgCost": position.avg_cost,
            "marketPrice": position.market_price,
            "unrealizedPnl": position.unrealized_pnl,
            "unrealizedPnlPct": position.unrealized_pnl_pct,
        }


async def _load_service() -> _PaperRouteService:
    return _PaperRouteService()


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/paper/orders", response_model=OrdersResponse)
async def get_orders(
    status: str | None = Query(None, pattern="^(pending|submitted|filled|partially_filled|cancelled|rejected)$"),
) -> OrdersResponse:
    service = await _load_service()
    return OrdersResponse(**(await service.get_orders(status=status)))


@router.get("/paper/positions", response_model=PositionsResponse)
async def get_positions() -> PositionsResponse:
    service = await _load_service()
    return PositionsResponse(**(await service.get_positions()))


@router.get("/paper/portfolio", response_model=PortfolioResponse)
async def get_portfolio() -> PortfolioResponse:
    service = await _load_service()
    return PortfolioResponse(**(await service.get_portfolio()))


@router.post("/paper/orders", status_code=201, response_model=PlaceOrderResponse)
async def place_order(req: PlaceOrderRequest) -> PlaceOrderResponse:
    service = await _load_service()
    return PlaceOrderResponse(**(await service.place_order(req)))


@router.delete("/paper/orders/{order_id}", response_model=CancelOrderResponse)
async def cancel_order(order_id: str) -> CancelOrderResponse:
    service = await _load_service()
    return CancelOrderResponse(**(await service.cancel_order(order_id)))


@router.post("/paper/reset", response_model=ResetResponse)
async def reset_paper() -> ResetResponse:
    service = await _load_service()
    return ResetResponse(**(await service.reset()))

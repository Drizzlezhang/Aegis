"""Paper trading API routes."""

import asyncio
import logging

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel, Field

from src.agents.strategy_exec.brokers.paper import PaperBroker
from src.models.paper import OrderSide, OrderType
from src.services.event_bus import get_event_bus
from src.services.portfolio_service import PortfolioService

from ..auth import verify_paper_token

logger = logging.getLogger(__name__)

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


# ── Dependency Injection (app.state) ─────────────────────────────────────────


async def get_broker(request: Request) -> PaperBroker:
    """Get PaperBroker from app.state (created once in lifespan)."""
    if not hasattr(request.app.state, "paper_broker"):
        raise HTTPException(status_code=503, detail="Paper trading not initialized")
    return request.app.state.paper_broker


async def get_portfolio(request: Request) -> PortfolioService:
    """Get PortfolioService from app.state (created once in lifespan)."""
    if not hasattr(request.app.state, "paper_portfolio"):
        raise HTTPException(status_code=503, detail="Paper trading not initialized")
    return request.app.state.paper_portfolio


# ── Service ──────────────────────────────────────────────────────────────────


class _PaperRouteService:
    def __init__(self, broker: PaperBroker, portfolio: PortfolioService) -> None:
        self._broker = broker
        self._portfolio = portfolio

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
        stats = await self._portfolio.get_stats()
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
        await self._broker.reset()
        await self._portfolio.reset()
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


async def _load_service(
    broker: PaperBroker = Depends(get_broker),
    portfolio: PortfolioService = Depends(get_portfolio),
) -> _PaperRouteService:
    return _PaperRouteService(broker, portfolio)


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/paper/orders", response_model=OrdersResponse, dependencies=[Depends(verify_paper_token)])
async def get_orders(
    status: str | None = Query(None, pattern="^(pending|submitted|filled|partially_filled|cancelled|rejected)$"),
    service: _PaperRouteService = Depends(_load_service),
) -> OrdersResponse:
    return OrdersResponse(**(await service.get_orders(status=status)))


@router.get("/paper/positions", response_model=PositionsResponse, dependencies=[Depends(verify_paper_token)])
async def get_positions(
    service: _PaperRouteService = Depends(_load_service),
) -> PositionsResponse:
    return PositionsResponse(**(await service.get_positions()))


@router.get("/paper/portfolio", response_model=PortfolioResponse, dependencies=[Depends(verify_paper_token)])
async def get_portfolio(
    service: _PaperRouteService = Depends(_load_service),
) -> PortfolioResponse:
    return PortfolioResponse(**(await service.get_portfolio()))


@router.post("/paper/orders", status_code=201, response_model=PlaceOrderResponse, dependencies=[Depends(verify_paper_token)])
async def place_order(
    req: PlaceOrderRequest,
    service: _PaperRouteService = Depends(_load_service),
) -> PlaceOrderResponse:
    return PlaceOrderResponse(**(await service.place_order(req)))


@router.delete("/paper/orders/{order_id}", response_model=CancelOrderResponse, dependencies=[Depends(verify_paper_token)])
async def cancel_order(
    order_id: str,
    service: _PaperRouteService = Depends(_load_service),
) -> CancelOrderResponse:
    return CancelOrderResponse(**(await service.cancel_order(order_id)))


@router.post("/paper/reset", response_model=ResetResponse, dependencies=[Depends(verify_paper_token)])
async def reset_paper(
    service: _PaperRouteService = Depends(_load_service),
) -> ResetResponse:
    return ResetResponse(**(await service.reset()))


# ── WebSocket ────────────────────────────────────────────────────────────────


@router.websocket("/paper/stream")
async def paper_stream(websocket: WebSocket) -> None:
    """Stream paper trading order events via WebSocket.

    Subscribes to EventBus OrderSubmittedEvent, OrderFilledEvent,
    OrderCancelledEvent, OrderRejectedEvent and pushes JSON frames.
    """
    await websocket.accept()
    logger.info("Paper WS client connected")

    bus = get_event_bus()
    queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=200)

    async def on_event(event) -> None:
        try:
            data = {
                "type": event.event_type,
                "timestamp": event.timestamp.isoformat() if hasattr(event, "timestamp") else "",
            }
            for attr in ("order_id", "symbol", "side", "order_type", "quantity",
                         "filled_quantity", "filled_avg_price", "remaining_quantity",
                         "limit_price", "reason"):
                if hasattr(event, attr):
                    data[attr] = getattr(event, attr)
            queue.put_nowait(data)
        except asyncio.QueueFull:
            logger.warning("Paper WS queue full, dropping event")

    handles = [
        bus.subscribe("OrderSubmittedEvent", on_event),
        bus.subscribe("OrderFilledEvent", on_event),
        bus.subscribe("OrderCancelledEvent", on_event),
        bus.subscribe("OrderRejectedEvent", on_event),
    ]

    try:
        while True:
            data = await queue.get()
            await websocket.send_json(data)
    except WebSocketDisconnect:
        logger.info("Paper WS client disconnected")
    finally:
        for h in handles:
            bus.unsubscribe(h)

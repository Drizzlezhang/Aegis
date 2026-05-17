"""WebSocket realtime price endpoints."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.agents.data_harvester.realtime import PriceUpdate, RealtimeManager

router = APIRouter()


def _serialize_update(kind: str, update: PriceUpdate) -> dict:
    return {
        "type": kind,
        "symbol": update.symbol.upper(),
        "price": update.price,
        "change": update.change,
        "change_pct": update.change_pct,
        "volume": update.volume,
        "timestamp": update.timestamp,
    }


@router.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket, symbols: str | None = None) -> None:
    """Stream realtime price snapshots and updates.

    Query params:
        symbols: optional comma-separated list, e.g. ``NVDA,TSLA``.
    """
    await websocket.accept()

    manager: RealtimeManager = websocket.app.state.realtime_manager
    queue = manager.subscribe()
    symbol_set = {s.strip().upper() for s in symbols.split(",") if s.strip()} if symbols else None

    try:
        for symbol, update in manager.get_all_latest().items():
            if symbol_set and symbol.upper() not in symbol_set:
                continue
            await websocket.send_json(_serialize_update("snapshot", update))

        while True:
            update = await queue.get()
            if symbol_set and update.symbol.upper() not in symbol_set:
                continue
            await websocket.send_json(_serialize_update("update", update))
    except WebSocketDisconnect:
        pass
    finally:
        manager.unsubscribe(queue)

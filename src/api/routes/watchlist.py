"""Watchlist API routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.services.watchlist import WatchlistService

router = APIRouter()

_service = WatchlistService()


class AddSymbolRequest(BaseModel):
    symbol: str
    notes: str = ""
    priority: int = 3


@router.get("/watchlist")
async def get_watchlist():
    return {"items": [item.model_dump(mode="json") for item in _service.list_items()]}


@router.post("/watchlist")
async def add_to_watchlist(req: AddSymbolRequest):
    try:
        item = _service.add(req.symbol, req.notes, req.priority)
        return {"item": item.model_dump(mode="json")}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str):
    if _service.remove(symbol):
        return {"removed": symbol}
    raise HTTPException(status_code=404, detail=f"{symbol} not in watchlist")
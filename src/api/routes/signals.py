"""Mock API routes for signals — Sprint16 Branch A contract."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query

router = APIRouter(tags=["signals"])


@router.get("")
async def list_signals(
    source: str | None = Query(None),
    sentiment: str | None = Query(None),
    since: datetime | None = Query(None),
    limit: int = Query(50, le=200),
) -> dict:
    # MOCK: B branch will replace with signal_event_store.list_events_since
    return {
        "items": [],  # B will fill
        "total": 0,
        "has_more": False,
        "_mock": True,
    }

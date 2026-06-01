"""Mock API routes for decisions — Sprint16 Branch A contract."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Query

from src.contracts.fixtures import make_fake_decision_context

router = APIRouter(tags=["decisions"])


@router.get("")
async def list_decisions(
    since: str | None = Query(None),
    symbol: str | None = Query(None),
    limit: int = Query(50),
) -> dict:
    # MOCK: C branch will replace with decision_log queries
    return {"items": [], "_mock": True}


@router.get("/{decision_id}/trace")
async def get_decision_trace(decision_id: str) -> dict:
    # MOCK: C branch will replace with decision_log trace lookup
    ctx = make_fake_decision_context()
    return {
        "decision_id": decision_id,
        "context_snapshot": ctx.context_snapshot,
        "signal_events": [asdict(s) for s in ctx.signal_events],
        "fused_signal": asdict(ctx.fused_signal),
        "_mock": True,
    }

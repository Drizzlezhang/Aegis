"""Decision API routes — Sprint16 Branch C real implementation."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter(tags=["decisions"])


@router.get("")
async def list_decisions(
    request: Request,
    symbol: str | None = Query(None),
    limit: int = Query(50),
) -> dict:
    decision_log = request.app.state.decision_log
    if symbol:
        items = await decision_log.query_by_symbol_raw(symbol, limit=limit)
    else:
        items = await decision_log.get_recent(days=90)
        items = items[:limit]
    return {"items": items}


@router.get("/{decision_id}/trace")
async def get_decision_trace(request: Request, decision_id: str) -> dict:
    decision_log = request.app.state.decision_log
    row = await decision_log.get_decision_by_id(decision_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Decision not found")

    # Deserialize context columns
    signals = []
    fusion = {}
    context_snapshot = {}

    if "signal_sources_json" in row and row["signal_sources_json"]:
        try:
            signals = json.loads(row["signal_sources_json"])
        except (json.JSONDecodeError, TypeError):
            signals = []

    if "fused_signal_json" in row and row["fused_signal_json"]:
        try:
            fusion = json.loads(row["fused_signal_json"])
        except (json.JSONDecodeError, TypeError):
            fusion = {}

    if "context_snapshot_json" in row and row["context_snapshot_json"]:
        try:
            context_snapshot = json.loads(row["context_snapshot_json"])
        except (json.JSONDecodeError, TypeError):
            context_snapshot = {}

    # Parse action/rationale from data_json
    action = row.get("decision_type", "")
    rationale = ""
    if "data_json" in row and row["data_json"]:
        try:
            data = json.loads(row["data_json"])
            rationale = data.get("reasoning", "")
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "decision_id": decision_id,
        "signals": signals,
        "fusion": fusion,
        "wyckoff_and_final": {
            "wyckoff_phase": context_snapshot.get("wyckoff_phase", ""),
            "action": action,
            "rationale": rationale,
            **context_snapshot,
        },
    }

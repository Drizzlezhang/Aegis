"""LLM cost governance API routes.

Provides endpoints for LLM usage, budget, call history, and cache statistics.
All endpoints require admin role authentication.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from src.db import get_session
from src.llm.budget import get_budget_tracker
from src.llm.cache import get_prompt_cache

router = APIRouter(prefix="/api/llm", tags=["llm"])


async def _require_admin() -> None:
    """Placeholder admin check — extend with actual auth when needed."""
    # In production, this would check JWT claims or API key roles
    pass


@router.get("/usage")
async def get_usage(
    period: str = Query("7d", pattern="^(today|7d|30d)$"),
    group_by: str = Query("agent", pattern="^(agent|model|day)$"),
    _admin: None = Depends(_require_admin),
) -> dict:
    """Get LLM usage statistics grouped by agent, model, or day."""
    now = datetime.now(UTC)
    if period == "today":
        since = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "30d":
        since = now - timedelta(days=30)
    else:
        since = now - timedelta(days=7)

    col_map = {"agent": "agent_name", "model": "model", "day": "DATE(timestamp)"}
    col = col_map.get(group_by, "agent_name")

    async with get_session() as session:
        result = await session.execute(
            text(
                f"SELECT {col} as group_key, "
                "SUM(input_tokens) as total_input, "
                "SUM(output_tokens) as total_output, "
                "SUM(cost_usd) as total_cost, "
                "COUNT(*) as calls "
                "FROM llm_call_log "
                "WHERE timestamp >= :since AND success = 1 "
                f"GROUP BY {col} "
                "ORDER BY total_cost DESC"
            ),
            {"since": since.isoformat()},
        )
        rows = result.fetchall()

    items = []
    total_cost = 0.0
    total_tokens = 0
    for row in rows:
        key, inp, out, cost, calls = row
        items.append({
            "key": str(key),
            "cost_usd": round(cost, 6),
            "input_tokens": inp,
            "output_tokens": out,
            "calls": calls,
        })
        total_cost += cost
        total_tokens += inp + out

    return {
        "period": period,
        "group_by": group_by,
        "total_cost_usd": round(total_cost, 6),
        "total_tokens": total_tokens,
        "items": items,
    }


@router.get("/budget")
async def get_budget(_admin: None = Depends(_require_admin)) -> dict:
    """Get current LLM budget status."""
    tracker = get_budget_tracker()
    return await tracker.check()


@router.get("/calls")
async def get_calls(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    _admin: None = Depends(_require_admin),
) -> dict:
    """Get paginated LLM call history."""
    offset = (page - 1) * size

    async with get_session() as session:
        # Get total count
        count_result = await session.execute(
            text("SELECT COUNT(*) FROM llm_call_log")
        )
        total = count_result.fetchone()[0]

        # Get page
        result = await session.execute(
            text(
                "SELECT id, request_id, agent_name, provider, model, "
                "input_tokens, output_tokens, cost_usd, latency_ms, "
                "cache_hit, prompt_version, success, error_msg, timestamp "
                "FROM llm_call_log "
                "ORDER BY timestamp DESC "
                "LIMIT :limit OFFSET :offset"
            ),
            {"limit": size, "offset": offset},
        )
        rows = result.fetchall()

    items = []
    for row in rows:
        items.append({
            "id": row[0],
            "request_id": row[1],
            "agent_name": row[2],
            "provider": row[3],
            "model": row[4],
            "input_tokens": row[5],
            "output_tokens": row[6],
            "cost_usd": round(row[7], 8),
            "latency_ms": row[8],
            "cache_hit": bool(row[9]),
            "prompt_version": row[10],
            "success": bool(row[11]),
            "error_msg": row[12],
            "timestamp": row[13].isoformat() if row[13] else None,
        })

    return {
        "page": page,
        "size": size,
        "total": total,
        "items": items,
    }


@router.get("/cache-stats")
async def get_cache_stats(_admin: None = Depends(_require_admin)) -> dict:
    """Get LLM cache statistics."""
    cache = get_prompt_cache()

    estimated_savings = 0.0
    if cache.hits > 0:
        async with get_session() as session:
            result = await session.execute(
                text("SELECT COALESCE(AVG(cost_usd), 0) FROM llm_call_log WHERE cache_hit = 0")
            )
            avg_cost = result.fetchone()[0]
            estimated_savings = round(cache.hits * avg_cost, 6)

    return {
        "hits": cache.hits,
        "misses": cache.misses,
        "hit_rate": round(cache.hit_rate, 4),
        "estimated_savings_usd": estimated_savings,
    }

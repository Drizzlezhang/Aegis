"""Signal API routes — query signal_events table."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from src.db import get_session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["signals"])


@router.get("")
async def list_signals(
    source: Annotated[str | None, Query()] = None,
    sentiment: Annotated[str | None, Query()] = None,
    since: Annotated[datetime | None, Query()] = None,
    limit: Annotated[int, Query(le=200)] = 50,
) -> dict:
    try:
        async with get_session() as session:
            # Normalize Query defaults (when called directly, not via FastAPI)
            _source = source if isinstance(source, str) else None
            _sentiment = sentiment if isinstance(sentiment, str) else None
            _since = since if isinstance(since, datetime) else None
            _limit = limit if isinstance(limit, int) else 50

            # Build query
            where_clauses = ["1=1"]
            params: dict = {}

            if _source:
                where_clauses.append("source = :source")
                params["source"] = _source
            if _sentiment:
                where_clauses.append("sentiment = :sentiment")
                params["sentiment"] = _sentiment
            if _since:
                where_clauses.append("timestamp >= :since")
                params["since"] = _since.isoformat()

            where_sql = " AND ".join(where_clauses)

            # Count total
            count_result = await session.execute(
                text(f"SELECT COUNT(*) FROM signal_events WHERE {where_sql}"),
                params,
            )
            total = count_result.scalar() or 0

            # Fetch page
            params["limit"] = _limit
            result = await session.execute(
                text(
                    f"SELECT * FROM signal_events "
                    f"WHERE {where_sql} "
                    f"ORDER BY timestamp DESC LIMIT :limit"
                ),
                params,
            )
            rows = result.fetchall()

            items = []
            for row in rows:
                item = dict(row._mapping)
                # Parse JSON fields
                if isinstance(item.get("symbols"), str):
                    try:
                        item["symbols"] = json.loads(item["symbols"])
                    except (json.JSONDecodeError, TypeError):
                        item["symbols"] = []
                if isinstance(item.get("metadata"), str):
                    try:
                        item["metadata"] = json.loads(item["metadata"])
                    except (json.JSONDecodeError, TypeError):
                        item["metadata"] = {}
                # Convert datetime to ISO string
                if isinstance(item.get("timestamp"), datetime):
                    item["timestamp"] = item["timestamp"].isoformat()
                items.append(item)

            return {
                "items": items,
                "total": total,
                "has_more": len(items) == limit,
            }
    except OperationalError:
        logger.debug("signal_events table not available, returning empty")
        return {"items": [], "total": 0, "has_more": False}

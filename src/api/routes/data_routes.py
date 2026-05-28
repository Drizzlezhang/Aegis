"""Data resilience API routes — breaker states, health scores."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/breakers")
async def get_breaker_states(request: Request) -> dict[str, Any]:
    """Return circuit breaker states for all data providers."""
    orchestrator = getattr(request.app.state, "_orchestrator", None)
    if orchestrator is None:
        return {"breakers": {}, "error": "orchestrator not initialized"}

    harvester = orchestrator.get_agent("Data-Harvester")
    if harvester is None or not hasattr(harvester, "_manager"):
        return {"breakers": {}, "error": "data harvester not available"}

    manager = harvester._manager
    breaker_states = manager.get_breaker_states()
    return {
        "breakers": {
            name: {
                "provider": bs.provider,
                "state": bs.state,
                "failure_count": bs.failure_count,
                "last_failure_at": bs.last_failure_at,
                "next_retry_at": bs.next_retry_at,
            }
            for name, bs in breaker_states.items()
        }
    }


@router.get("/health")
async def get_provider_health(request: Request) -> dict[str, Any]:
    """Return health scores for all data providers."""
    orchestrator = getattr(request.app.state, "_orchestrator", None)
    if orchestrator is None:
        return {"providers": {}, "error": "orchestrator not initialized"}

    harvester = orchestrator.get_agent("Data-Harvester")
    if harvester is None or not hasattr(harvester, "_manager"):
        return {"providers": {}, "error": "data harvester not available"}

    manager = harvester._manager
    metrics = manager.get_fetcher_metrics()

    providers = {}
    for name, m in metrics.items():
        success_rate = m.success_count / m.total_calls if m.total_calls > 0 else 0.0
        providers[name] = {
            "provider": name,
            "total_calls": m.total_calls,
            "success_count": m.success_count,
            "error_count": m.error_count,
            "success_rate": round(success_rate, 4),
            "avg_latency_ms": round(m.avg_latency_ms, 2),
            "circuit_state": m.circuit_state.value,
            "last_success": m.last_success.isoformat() if m.last_success else None,
            "last_error": m.last_error.isoformat() if m.last_error else None,
        }

    return {"providers": providers}

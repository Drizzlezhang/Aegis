"""Decision tracking API routes."""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/tracking/stats")
async def get_tracking_stats(request: Request):
    """Return tracking hit-rate statistics."""
    tracking = request.app.state.tracking_service
    return tracking.get_stats()


@router.get("/tracking/decisions")
async def get_tracked_decisions(request: Request, limit: int = 20):
    """Return the most recent tracked decisions."""
    tracking = request.app.state.tracking_service
    decisions = tracking.list_recent(limit=limit)
    return {"decisions": [d.model_dump(mode="json") for d in decisions]}


@router.post("/tracking/update")
async def update_tracking(request: Request):
    """Manually trigger a tracking status update."""
    tracking = request.app.state.tracking_service
    await tracking.update_all()
    return {"status": "updated", "stats": tracking.get_stats()}

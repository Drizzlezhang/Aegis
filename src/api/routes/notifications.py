"""Notification API routes."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()


class NotificationHistoryResponse(BaseModel):
    notifications: list[dict]
    unread_count: int


def _serialize(n) -> dict:
    return {
        "id": n.id,
        "level": n.level.value,
        "category": n.category.value,
        "title": n.title,
        "message": n.message,
        "created_at": n.created_at.isoformat(),
        "read": n.read,
        "metadata": n.metadata,
    }


@router.get("/notifications")
async def get_notifications(
    request: Request,
    limit: int = 50,
    category: str | None = None,
) -> NotificationHistoryResponse:
    """Get notification history."""
    from src.services.notification.base import NotificationCategory

    router_service = request.app.state.notification_router
    cat = NotificationCategory(category) if category else None
    history = router_service.get_history(limit=limit, category=cat)
    return NotificationHistoryResponse(
        notifications=[_serialize(n) for n in history],
        unread_count=router_service.unread_count,
    )


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(request: Request, notification_id: str) -> dict:
    """Mark a notification as read."""
    router_service = request.app.state.notification_router
    success = router_service.mark_read(notification_id)
    if not success:
        raise HTTPException(404, "Notification not found")
    return {"success": True}


@router.post("/notifications/mark-all-read")
async def mark_all_read(request: Request) -> dict:
    """Mark all notifications as read."""
    router_service = request.app.state.notification_router
    for n in router_service._history:
        n.read = True
    return {"success": True, "count": len(router_service._history)}


@router.get("/notifications/channels")
async def get_channels(request: Request) -> dict:
    """List configured notification channels and their status."""
    router_service = request.app.state.notification_router
    channels = []
    for name, channel in router_service._channels.items():
        channels.append({
            "type": name,
            "available": await channel.is_available(),
        })
    return {"channels": channels}

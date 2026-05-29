"""Settings API routes."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


@router.get("/settings")
async def get_settings(request: Request):
    """获取当前设置。"""
    service = request.app.state.settings_service
    settings = service.get_current()
    return settings.model_dump()


class UpdateSettingsRequest(BaseModel):
    telegram: dict | None = None
    notifications: dict | None = None
    scheduler: dict | None = None
    confidence_threshold: float | None = None
    silent_hours_start: int | None = None
    silent_hours_end: int | None = None


@router.put("/settings")
async def update_settings(request: Request, req: UpdateSettingsRequest):
    """更新设置（部分更新）。"""
    service = request.app.state.settings_service
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    settings = service.update(updates)
    service.apply_to_runtime(request.app.state)
    return settings.model_dump()


@router.post("/settings/test-telegram")
async def test_telegram(request: Request):
    """发送测试消息验证 Telegram 配置。"""
    try:
        from src.services.notification.telegram import TelegramNotifier

        notifier = TelegramNotifier()
        success = await notifier.send_message("Aegis-Trader: Test notification — configuration is working!", force=True)
        await notifier.close()
        return {"success": success}
    except (ImportError, ModuleNotFoundError):
        return {"success": False, "reason": "Telegram notifier not available"}

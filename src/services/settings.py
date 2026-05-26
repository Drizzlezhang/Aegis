"""Settings persistence service — 用户可修改的运行时配置。"""

import json
import logging
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger(__name__)

SETTINGS_PATH = Path("~/.aegis-trader/settings.json").expanduser()


class TelegramSettings(BaseModel):
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""


class NotificationSettings(BaseModel):
    notify_on_high_confidence: bool = True
    notify_on_completion: bool = True
    notify_on_error: bool = True


class SchedulerSettings(BaseModel):
    enabled: bool = True
    daily_run_time: str = "09:30"
    timezone: str = "America/New_York"
    max_concurrent_analyses: int = 3


class UserSettings(BaseModel):
    telegram: TelegramSettings = TelegramSettings()
    notifications: NotificationSettings = NotificationSettings()
    scheduler: SchedulerSettings = SchedulerSettings()
    confidence_threshold: float = 0.7
    silent_hours_start: int = 23
    silent_hours_end: int = 7


class SettingsService:
    """管理用户可修改的运行时设置。"""

    def __init__(self):
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._settings = self._load()

    def _load(self) -> UserSettings:
        """从文件加载设置，不存在则使用默认值。"""
        if SETTINGS_PATH.exists():
            try:
                data = json.loads(SETTINGS_PATH.read_text())
                return UserSettings(**data)
            except Exception as e:
                logger.warning(f"Failed to load settings: {e}, using defaults")

        return UserSettings()

    def _save(self):
        """持久化到 JSON 文件。"""
        SETTINGS_PATH.write_text(
            json.dumps(self._settings.model_dump(), indent=2)
        )

    def get_current(self) -> UserSettings:
        """获取当前设置。"""
        return self._settings

    def update(self, updates: dict) -> UserSettings:
        """部分更新设置。"""
        current_data = self._settings.model_dump()

        # 深度合并
        for key, value in updates.items():
            if key in current_data:
                if isinstance(current_data[key], dict) and isinstance(value, dict):
                    current_data[key].update(value)
                else:
                    current_data[key] = value

        self._settings = UserSettings(**current_data)
        self._save()
        return self._settings

    def apply_to_runtime(self, app_state) -> None:
        """Apply current settings to runtime services."""
        settings = self._settings

        # 1. Update scheduler intervals if changed
        if hasattr(app_state, 'scheduler'):
            scheduler = app_state.scheduler
            try:
                tracking_time = getattr(settings.scheduler, 'daily_run_time', '16:30')
                hour, minute = map(int, tracking_time.split(":"))
                scheduler.reschedule_job("tracking_update",
                                         hour=hour, minute=minute,
                                         day_of_week="mon-fri")
            except Exception as e:
                logger.warning(f"Failed to reschedule tracking_update: {e}")

        # 2. Update notification settings
        if hasattr(app_state, 'notification_settings'):
            app_state.notification_settings = {
                "notify_on_high_confidence": settings.notifications.notify_on_high_confidence,
                "notify_on_completion": settings.notifications.notify_on_completion,
                "notify_on_error": settings.notifications.notify_on_error,
            }

        logger.info("Settings applied to runtime")
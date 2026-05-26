"""Abstract notification channel interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class NotificationLevel(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    ERROR = "error"


class NotificationCategory(StrEnum):
    ANALYSIS = "analysis"
    POSITION = "position"
    SYSTEM = "system"
    TRACKING = "tracking"


@dataclass
class Notification:
    """Unified notification payload."""

    id: str
    level: NotificationLevel
    category: NotificationCategory
    title: str
    message: str
    created_at: datetime
    metadata: dict | None = None
    read: bool = False


class NotificationChannel(ABC):
    """Base class for all notification channels."""

    @property
    @abstractmethod
    def channel_type(self) -> str:
        """Channel identifier (e.g., 'telegram', 'webhook')."""
        ...

    @abstractmethod
    async def send(self, notification: Notification) -> bool:
        """Send a notification. Returns True on success."""
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if channel is properly configured and reachable."""
        ...

    async def close(self) -> None:
        """Cleanup resources."""
        pass

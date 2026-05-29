"""Notification routing — dispatch by level/category to configured channels."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from .base import Notification, NotificationCategory, NotificationChannel, NotificationLevel


@dataclass
class RoutingRule:
    """A rule mapping level+category to channel(s)."""

    channel_type: str
    min_level: NotificationLevel = NotificationLevel.INFO
    categories: list[NotificationCategory] | None = None  # None = all categories


class NotificationRouter:
    """Route notifications to appropriate channels based on rules."""

    def __init__(self):
        self._channels: dict[str, NotificationChannel] = {}
        self._rules: list[RoutingRule] = []
        self._history: list[Notification] = []
        self._max_history = 200

    def register_channel(self, channel: NotificationChannel) -> None:
        """Register a notification channel."""
        self._channels[channel.channel_type] = channel

    def add_rule(self, rule: RoutingRule) -> None:
        """Add a routing rule."""
        self._rules.append(rule)

    def set_rules(self, rules: list[RoutingRule]) -> None:
        """Replace all routing rules."""
        self._rules = rules

    async def dispatch(
        self,
        level: NotificationLevel,
        category: NotificationCategory,
        title: str,
        message: str,
        metadata: dict | None = None,
    ) -> list[str]:
        """Dispatch notification to matching channels. Returns list of channels that succeeded."""
        notification = Notification(
            id=uuid4().hex[:12],
            level=level,
            category=category,
            title=title,
            message=message,
            created_at=datetime.now(UTC),
            metadata=metadata,
        )

        self._history.append(notification)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        target_channels = self._resolve_channels(level, category)

        succeeded = []
        for channel_type in target_channels:
            channel = self._channels.get(channel_type)
            if channel and await channel.send(notification):
                succeeded.append(channel_type)

        return succeeded

    def get_history(self, limit: int = 50, category: NotificationCategory | None = None) -> list[Notification]:
        """Get recent notification history."""
        history = self._history
        if category:
            history = [n for n in history if n.category == category]
        return list(reversed(history[-limit:]))

    def mark_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        for n in self._history:
            if n.id == notification_id:
                n.read = True
                return True
        return False

    @property
    def unread_count(self) -> int:
        return sum(1 for n in self._history if not n.read)

    def _resolve_channels(self, level: NotificationLevel, category: NotificationCategory) -> set[str]:
        """Determine which channels should receive this notification."""
        level_order = {
            NotificationLevel.INFO: 0,
            NotificationLevel.WARNING: 1,
            NotificationLevel.CRITICAL: 2,
            NotificationLevel.ERROR: 3,
        }
        targets: set[str] = set()
        for rule in self._rules:
            if level_order.get(level, 0) >= level_order.get(rule.min_level, 0):
                if rule.categories is None or category in rule.categories:
                    targets.add(rule.channel_type)
        return targets

    async def close(self) -> None:
        """Cleanup all channels."""
        for channel in self._channels.values():
            await channel.close()

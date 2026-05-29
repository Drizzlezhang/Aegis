"""Telegram Bot notification service."""

import logging
from datetime import datetime

import httpx

from src.config import get_config

from .base import Notification, NotificationChannel, NotificationLevel

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramNotifier(NotificationChannel):
    """通过 Telegram Bot API 发送通知。"""

    def __init__(self):
        config = get_config()
        self._config = config.telegram
        self._client = httpx.AsyncClient(timeout=10)

    @property
    def channel_type(self) -> str:
        return "telegram"

    @property
    def enabled(self) -> bool:
        return self._config.enabled and bool(self._config.bot_token) and bool(self._config.chat_id)

    def _in_silent_hours(self) -> bool:
        hour = datetime.now().hour
        start, end = self._config.silent_hours
        if start > end:
            return hour >= start or hour < end
        return start <= hour < end

    async def send(self, notification: Notification) -> bool:
        """Send a Notification object via Telegram (NotificationChannel interface)."""
        force = notification.level in (NotificationLevel.CRITICAL, NotificationLevel.ERROR)
        return await self._send_text(self._format_notification(notification), force=force)

    async def is_available(self) -> bool:
        """Check if Telegram channel is properly configured."""
        return self.enabled

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    # ── legacy public API (backward compatible) ──────────────────────────

    async def send_message(self, message: str, force: bool = False) -> bool:
        """发送消息到 Telegram。静默时段内不发送（除非 force=True）。"""
        return await self._send_text(message, force=force)

    async def notify_analysis_complete(
        self, symbol: str, recommendations: list, confidence: float
    ):
        """分析完成通知。"""
        if not self._config.notify_on_completion:
            return
        msg = f"📊 *{symbol} 分析完成*\n"
        msg += f"推荐策略数: {len(recommendations)}\n"
        if recommendations and confidence >= self._config.confidence_threshold:
            rec = recommendations[0]
            msg += "\n🎯 *Top 推荐:*\n"
            msg += f" 策略: {rec.get('strategy_type', 'N/A')}\n"
            msg += f" 置信度: {confidence:.0%}\n"
            msg += f" 入场: ${rec.get('entry_price', 'N/A')}\n"
        await self._send_text(msg)

    async def notify_daily_summary(self, results: list[dict]):
        """每日调度完成汇总。"""
        total = len(results)
        success = sum(1 for r in results if r.get("success"))
        high_conf = sum(1 for r in results if r.get("high_confidence"))

        msg = "📋 *每日分析汇总*\n"
        msg += f"分析标的: {total} | 成功: {success} | 高置信度推荐: {high_conf}\n"
        if high_conf > 0:
            msg += "\n🔥 *高置信度标的:*\n"
            for r in results:
                if r.get("high_confidence"):
                    msg += f" • {r['symbol']}: {r.get('top_strategy', 'N/A')}\n"
        await self._send_text(msg)

    async def notify_error(self, context: str, error: str):
        """系统错误通知。"""
        if not self._config.notify_on_error:
            return
        msg = f"⚠️ *系统异常*\n场景: {context}\n错误: `{error[:200]}`"
        await self._send_text(msg, force=True)

    async def send_tracking_summary(self, stats: dict) -> bool:
        """Send daily tracking performance summary."""
        total = stats.get("total", 0)
        hit_rate = stats.get("hit_rate", 0)
        avg_pnl = stats.get("avg_pnl_pct", 0)
        pending = stats.get("pending", 0)

        message = (
            "📊 Aegis Daily Tracking Summary\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Total Tracked: {total}\n"
            f"Hit Rate: {hit_rate:.1%}\n"
            f"Avg PnL: {avg_pnl:+.2f}%\n"
            f"Pending: {pending}\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        return await self._send_text(message)

    # ── internal ─────────────────────────────────────────────────────────

    def _format_notification(self, notification: Notification) -> str:
        """Format a Notification object as a Telegram message."""
        level_emoji = {
            NotificationLevel.INFO: "ℹ️",
            NotificationLevel.WARNING: "⚠️",
            NotificationLevel.CRITICAL: "🔴",
            NotificationLevel.ERROR: "🚨",
        }
        emoji = level_emoji.get(notification.level, "📢")
        return (
            f"{emoji} *{notification.title}*\n"
            f"{notification.message}\n"
            f"_{notification.category.value} | {notification.created_at.strftime('%Y-%m-%d %H:%M UTC')}_"
        )

    async def _send_text(self, text: str, force: bool = False) -> bool:
        """Internal: send raw text to Telegram."""
        if not self.enabled:
            return False
        if self._in_silent_hours() and not force:
            logger.debug("In silent hours, skipping notification")
            return False

        url = TELEGRAM_API.format(token=self._config.bot_token)
        payload = {
            "chat_id": self._config.chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }
        try:
            resp = await self._client.post(url, json=payload)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False

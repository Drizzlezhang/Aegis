"""Telegram Bot notification service."""

import logging
from datetime import datetime

import httpx

from src.config import get_config

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramNotifier:
    """通过 Telegram Bot API 发送通知。"""

    def __init__(self):
        config = get_config()
        self._config = config.telegram
        self._client = httpx.AsyncClient(timeout=10)

    @property
    def enabled(self) -> bool:
        return self._config.enabled and bool(self._config.bot_token) and bool(self._config.chat_id)

    def _in_silent_hours(self) -> bool:
        hour = datetime.now().hour
        start, end = self._config.silent_hours
        if start > end:
            # 跨午夜
            return hour >= start or hour < end
        return start <= hour < end

    async def send(self, message: str, force: bool = False) -> bool:
        """发送消息到 Telegram。静默时段内不发送（除非 force=True）。"""
        if not self.enabled:
            return False
        if self._in_silent_hours() and not force:
            logger.debug("In silent hours, skipping notification")
            return False

        url = TELEGRAM_API.format(token=self._config.bot_token)
        payload = {
            "chat_id": self._config.chat_id,
            "text": message,
            "parse_mode": "Markdown",
        }
        try:
            resp = await self._client.post(url, json=payload)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False

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
            msg += f"\n🎯 *Top 推荐:*\n"
            msg += f" 策略: {rec.get('strategy_type', 'N/A')}\n"
            msg += f" 置信度: {confidence:.0%}\n"
            msg += f" 入场: ${rec.get('entry_price', 'N/A')}\n"
        await self.send(msg)

    async def notify_daily_summary(self, results: list[dict]):
        """每日调度完成汇总。"""
        total = len(results)
        success = sum(1 for r in results if r.get("success"))
        high_conf = sum(1 for r in results if r.get("high_confidence"))

        msg = f"📋 *每日分析汇总*\n"
        msg += f"分析标的: {total} | 成功: {success} | 高置信度推荐: {high_conf}\n"
        if high_conf > 0:
            msg += f"\n🔥 *高置信度标的:*\n"
            for r in results:
                if r.get("high_confidence"):
                    msg += f" • {r['symbol']}: {r.get('top_strategy', 'N/A')}\n"
        await self.send(msg)

    async def notify_error(self, context: str, error: str):
        """系统错误通知。"""
        if not self._config.notify_on_error:
            return
        msg = f"⚠️ *系统异常*\n场景: {context}\n错误: `{error[:200]}`"
        await self.send(msg, force=True)
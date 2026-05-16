"""Anti-whipsaw: 24 小时内同一 symbol 不翻转决策方向。"""

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class AntiWhipsaw:
    """决策稳定化器。"""

    def __init__(
        self,
        cooldown_hours: int = 24,
        state_file: str = "~/.aegis-trader/whipsaw_state.json",
    ):
        self._cooldown = timedelta(hours=cooldown_hours)
        self._state_file = Path(state_file).expanduser()
        self._decisions: dict[str, dict] = {}
        self._load_state()

    def should_allow(self, symbol: str, new_direction: str) -> tuple[bool, str]:
        """检查是否允许新决策方向。

        Returns:
            (allowed, reason)
        """
        symbol = symbol.upper()
        if symbol not in self._decisions:
            return True, "first_decision"

        record = self._decisions[symbol]
        last_direction = record.get("direction", "")
        last_ts_str = record.get("timestamp", "")

        try:
            last_ts = datetime.fromisoformat(last_ts_str)
        except (ValueError, TypeError):
            return True, "invalid_timestamp"

        now = datetime.now(timezone.utc)
        if now - last_ts > self._cooldown:
            return True, "cooldown_expired"

        if new_direction == "neutral" or last_direction == "neutral":
            return True, "neutral_direction"

        if new_direction == last_direction:
            return True, "same_direction"

        remaining = self._cooldown - (now - last_ts)
        hours_left = remaining.total_seconds() / 3600
        reason = (
            f"flip_blocked: {last_direction} → {new_direction}, "
            f"cooldown remaining: {hours_left:.1f}h"
        )
        return False, reason

    def record_decision(self, symbol: str, direction: str) -> None:
        """记录新决策方向和时间。"""
        symbol = symbol.upper()
        self._decisions[symbol] = {
            "direction": direction,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._save_state()

    def clear(self, symbol: str | None = None) -> None:
        """清除冷却状态。"""
        if symbol:
            self._decisions.pop(symbol.upper(), None)
        else:
            self._decisions.clear()
        self._save_state()

    def _load_state(self) -> None:
        """从 JSON 文件加载状态。"""
        try:
            if self._state_file.exists():
                data = json.loads(self._state_file.read_text())
                if isinstance(data, dict):
                    self._decisions = data
                    logger.debug(f"Loaded whipsaw state: {len(self._decisions)} records")
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load whipsaw state: {e}, starting fresh")
            self._decisions = {}

    def _save_state(self) -> None:
        """持久化到 JSON 文件。"""
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            self._state_file.write_text(json.dumps(self._decisions, indent=2))
        except OSError as e:
            logger.warning(f"Failed to save whipsaw state: {e}")
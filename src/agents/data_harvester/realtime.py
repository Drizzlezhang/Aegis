"""实时行情发布/订阅管理器。"""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

from src.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class PriceUpdate:
    symbol: str
    price: float
    change: float
    change_pct: float
    volume: int
    timestamp: float
    source: str


class RealtimeManager:
    """管理实时行情订阅与分发。

    1. 接收 fetcher 发布的价格更新
    2. 维护 symbol → 最新价格 缓存
    3. asyncio.Queue 分发给订阅者（支持背压控制）
    4. 过期数据自动过滤
    5. 心跳检测与指数退避重连
    """

    def __init__(self, stale_threshold_seconds: float = 60.0):
        config = get_config().realtime
        self._subscribers: list[asyncio.Queue[PriceUpdate]] = []
        self._latest: dict[str, PriceUpdate] = {}
        self._stale_threshold = stale_threshold_seconds
        self._queue_size = config.subscriber_queue_size
        self._backpressure = config.backpressure_strategy

        # Heartbeat / reconnect state
        self._heartbeat_interval = config.heartbeat_interval_seconds
        self._heartbeat_timeout = config.heartbeat_timeout_seconds
        self._max_reconnect_attempts = config.max_reconnect_attempts
        self._reconnect_base_delay = config.reconnect_base_delay
        self._reconnect_max_delay = config.reconnect_max_delay
        self._heartbeat_task: asyncio.Task | None = None
        self._reconnect_attempts = 0
        self._disabled = False
        self._last_heartbeat = 0.0

        # Callbacks set by the data harvester
        self._on_heartbeat: Callable | None = None
        self._on_reconnect: Callable | None = None

    # ── Backpressure (E3) ──────────────────────────────────────────

    async def publish(self, update: PriceUpdate) -> None:
        self._latest[update.symbol.upper()] = update
        for queue in self._subscribers:
            await self._publish_to_queue(queue, update)

    async def _publish_to_queue(
        self, queue: asyncio.Queue[PriceUpdate], update: PriceUpdate
    ) -> None:
        """Publish to a single subscriber queue with backpressure strategy."""
        if self._backpressure == "drop_oldest":
            try:
                queue.put_nowait(update)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()  # discard oldest
                except asyncio.QueueEmpty:
                    pass
                try:
                    queue.put_nowait(update)
                except asyncio.QueueFull:
                    pass
        elif self._backpressure == "throttle":
            try:
                queue.put_nowait(update)
            except asyncio.QueueFull:
                pass  # drop current message
        elif self._backpressure == "block":
            await queue.put(update)
        else:
            try:
                queue.put_nowait(update)
            except asyncio.QueueFull:
                pass

    def subscribe(self, max_queue_size: int | None = None) -> asyncio.Queue[PriceUpdate]:
        size = max_queue_size if max_queue_size is not None else self._queue_size
        queue: asyncio.Queue[PriceUpdate] = asyncio.Queue(maxsize=size)
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[PriceUpdate]) -> None:
        self._subscribers = [q for q in self._subscribers if q is not queue]

    # ── Heartbeat & Reconnect (E4) ─────────────────────────────────

    @property
    def disabled(self) -> bool:
        return self._disabled

    @property
    def reconnect_attempts(self) -> int:
        return self._reconnect_attempts

    def set_heartbeat_callback(self, callback: Callable) -> None:
        """Set the async heartbeat check function (e.g. ping websocket)."""
        self._on_heartbeat = callback

    def set_reconnect_callback(self, callback: Callable) -> None:
        """Set the async reconnect function."""
        self._on_reconnect = callback

    async def start_heartbeat(self) -> None:
        """Start heartbeat monitoring as an independent asyncio task."""
        if self._heartbeat_task is not None:
            return
        self._last_heartbeat = time.monotonic()
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def stop_heartbeat(self) -> None:
        """Stop heartbeat monitoring."""
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None

    def record_heartbeat(self) -> None:
        """Call this when a heartbeat response is received."""
        self._last_heartbeat = time.monotonic()
        self._reconnect_attempts = 0

    async def _heartbeat_loop(self) -> None:
        """Heartbeat monitoring loop with exponential backoff reconnect."""
        while not self._disabled:
            await asyncio.sleep(self._heartbeat_interval)

            if self._disabled:
                break

            # Check if heartbeat is stale
            elapsed = time.monotonic() - self._last_heartbeat
            if elapsed > self._heartbeat_timeout:
                logger.warning(
                    f"Heartbeat timeout ({elapsed:.1f}s > {self._heartbeat_timeout}s), "
                    f"attempting reconnect ({self._reconnect_attempts + 1}/{self._max_reconnect_attempts})"
                )
                success = await self._try_reconnect()
                if not success:
                    self._reconnect_attempts += 1
                    if self._reconnect_attempts >= self._max_reconnect_attempts:
                        logger.error(
                            f"Max reconnect attempts ({self._max_reconnect_attempts}) reached, "
                            "entering disabled state"
                        )
                        self._disabled = True
                        return

    async def _try_reconnect(self) -> bool:
        """Attempt reconnection with exponential backoff. Returns True on success."""
        if self._on_reconnect is None:
            return False

        delay = min(
            self._reconnect_base_delay * (2 ** self._reconnect_attempts),
            self._reconnect_max_delay,
        )
        logger.info(f"Reconnecting in {delay:.1f}s (attempt {self._reconnect_attempts + 1})")
        await asyncio.sleep(delay)

        try:
            await self._on_reconnect()
            self._last_heartbeat = time.monotonic()
            self._reconnect_attempts = 0
            logger.info("Reconnect successful")
            return True
        except Exception as e:
            logger.warning(f"Reconnect failed: {e}")
            return False

    # ── Data access ─────────────────────────────────────────────────

    def shutdown(self) -> None:
        """清理订阅者与最新行情缓存。"""
        self._subscribers.clear()
        self._latest.clear()
        self._disabled = True

    def get_latest(self, symbol: str) -> PriceUpdate | None:
        update = self._latest.get(symbol.upper())
        if update and (time.time() - update.timestamp) > self._stale_threshold:
            return None
        return update

    def get_all_latest(self) -> dict[str, PriceUpdate]:
        now = time.time()
        return {s: u for s, u in self._latest.items() if (now - u.timestamp) <= self._stale_threshold}

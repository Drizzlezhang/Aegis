"""实时行情发布/订阅管理器。"""

from dataclasses import dataclass
import asyncio
import time


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
    3. asyncio.Queue 分发给订阅者
    4. 过期数据自动过滤
    """

    def __init__(self, stale_threshold_seconds: float = 60.0):
        self._subscribers: list[asyncio.Queue[PriceUpdate]] = []
        self._latest: dict[str, PriceUpdate] = {}
        self._stale_threshold = stale_threshold_seconds

    async def publish(self, update: PriceUpdate) -> None:
        self._latest[update.symbol.upper()] = update
        for queue in self._subscribers:
            try:
                queue.put_nowait(update)
            except asyncio.QueueFull:
                pass

    def subscribe(self, max_queue_size: int = 100) -> asyncio.Queue[PriceUpdate]:
        queue: asyncio.Queue[PriceUpdate] = asyncio.Queue(maxsize=max_queue_size)
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[PriceUpdate]) -> None:
        self._subscribers = [q for q in self._subscribers if q is not queue]

    def get_latest(self, symbol: str) -> PriceUpdate | None:
        update = self._latest.get(symbol.upper())
        if update and (time.time() - update.timestamp) > self._stale_threshold:
            return None
        return update

    def get_all_latest(self) -> dict[str, PriceUpdate]:
        now = time.time()
        return {s: u for s, u in self._latest.items() if (now - u.timestamp) <= self._stale_threshold}
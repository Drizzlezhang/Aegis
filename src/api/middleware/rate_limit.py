"""Token bucket rate limiter middleware."""

import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """基于 IP 的 token bucket 限流。"""

    def __init__(self, app, rate: float = 120, per: float = 60.0):
        super().__init__(app)
        self.rate = rate
        self.per = per
        self._buckets: dict[str, dict] = defaultdict(
            lambda: {"tokens": rate, "last": time.monotonic()}
        )

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        bucket = self._buckets[client_ip]

        now = time.monotonic()
        elapsed = now - bucket["last"]
        bucket["last"] = now
        bucket["tokens"] = min(
            self.rate, bucket["tokens"] + elapsed * (self.rate / self.per)
        )

        if bucket["tokens"] < 1:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})

        bucket["tokens"] -= 1
        return await call_next(request)
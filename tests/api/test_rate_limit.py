"""Tests for rate limit middleware."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.middleware.rate_limit import RateLimitMiddleware


def _make_app(rate: float = 120):
    app = FastAPI()

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    app.add_middleware(RateLimitMiddleware, rate=rate, per=60)
    return app


def test_requests_within_limit():
    client = TestClient(_make_app())
    for _ in range(10):
        response = client.get("/api/health")
        assert response.status_code == 200


def test_rate_limit_exceeded():
    client = TestClient(_make_app(rate=5))
    for i in range(50):
        response = client.get("/api/health")
        if response.status_code == 429:
            assert i > 3
            return
    pytest.fail("Expected 429 but never received")
"""Tests for JWT + API Key auth middleware."""

import time

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.middleware.auth import AuthMiddleware
from src.config import set_config, get_config

JWT_SECRET = "test-secret-key-for-middleware"
API_KEYS = ["test-api-key-1", "test-api-key-2"]


def _make_app():
    """Create a minimal FastAPI app with AuthMiddleware."""
    app = FastAPI()

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/symbols")
    async def symbols():
        return {"symbols": []}

    @app.get("/openapi.json")
    async def openapi():
        return {"openapi": "3.0"}

    app.add_middleware(AuthMiddleware)
    return app


@pytest.fixture(autouse=True)
def configure_auth():
    original = get_config()
    try:
        config = original.model_copy(deep=True)
        config.auth.enabled = True
        config.auth.jwt_secret = JWT_SECRET
        config.auth.api_keys = API_KEYS
        set_config(config)
        yield
    finally:
        set_config(original)


def _make_token(exp_offset: int = 3600) -> str:
    payload = {
        "sub": "test-user",
        "iat": int(time.time()),
        "exp": int(time.time()) + exp_offset,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def test_public_path_no_auth():
    response = TestClient(_make_app()).get("/api/health")
    assert response.status_code == 200


def test_valid_jwt_passes():
    token = _make_token()
    response = TestClient(_make_app()).get(
        "/api/symbols",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_expired_jwt_rejected():
    token = _make_token(exp_offset=-3600)
    response = TestClient(_make_app()).get(
        "/api/symbols",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


def test_valid_api_key_passes():
    response = TestClient(_make_app()).get(
        "/api/symbols",
        headers={"X-API-Key": API_KEYS[0]},
    )
    assert response.status_code == 200


def test_verify_token_expired():
    token = _make_token(exp_offset=-3600)
    assert not AuthMiddleware._verify_token(token, get_config())


def test_verify_token_valid():
    token = _make_token()
    assert AuthMiddleware._verify_token(token, get_config())
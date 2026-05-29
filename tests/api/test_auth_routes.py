"""Tests for auth API routes."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.auth import router as auth_router
from src.config import get_config, set_config

API_KEYS = ["login-test-key"]


def _make_app():
    app = FastAPI()
    app.include_router(auth_router, prefix="/api")
    return app


@pytest.fixture(autouse=True)
def configure_auth():
    original = get_config()
    try:
        config = original.model_copy(deep=True)
        config.auth.api_keys = API_KEYS
        config.auth.jwt_secret = "login-test-secret-here"
        set_config(config)
        yield
    finally:
        set_config(original)


def test_login_success():
    response = TestClient(_make_app()).post(
        "/api/auth/login",
        json={"api_key": API_KEYS[0]},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


def test_login_invalid_key():
    response = TestClient(_make_app()).post(
        "/api/auth/login",
        json={"api_key": "wrong-key"},
    )
    assert response.status_code == 401
    assert "Invalid API key" in response.json()["detail"]

"""Authentication routes."""

import time

import jwt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.config import get_config

router = APIRouter()


class LoginRequest(BaseModel):
    api_key: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post("/auth/login")
async def login(req: LoginRequest) -> TokenResponse:
    """用 API Key 换取 JWT Token。"""
    config = get_config()
    if req.api_key not in config.auth.api_keys:
        raise HTTPException(status_code=401, detail="Invalid API key")

    expires_in = config.auth.access_token_expire_minutes * 60
    payload = {
        "sub": "aegis-user",
        "iat": int(time.time()),
        "exp": int(time.time()) + expires_in,
    }
    token = jwt.encode(
        payload, config.auth.jwt_secret, algorithm=config.auth.jwt_algorithm
    )
    return TokenResponse(access_token=token, expires_in=expires_in)

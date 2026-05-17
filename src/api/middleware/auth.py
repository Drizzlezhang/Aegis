"""JWT + API Key authentication middleware."""

import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import jwt

from src.config import get_config

PUBLIC_PATHS = {"/api/health", "/api/auth/login", "/docs", "/openapi.json"}


class AuthMiddleware(BaseHTTPMiddleware):
    """统一认证中间件。支持 JWT Bearer Token 和静态 API Key。"""

    async def dispatch(self, request: Request, call_next):
        config = get_config()

        if not config.auth.enabled:
            return await call_next(request)

        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        if request.url.path.startswith("/ws/"):
            token = request.query_params.get("token")
            if not token or not self._verify_token(token, config):
                return JSONResponse(status_code=403, content={"detail": "WebSocket auth required"})
            return await call_next(request)

        api_key = request.headers.get(config.auth.api_key_header)
        if api_key and api_key in config.auth.api_keys:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            if self._verify_token(token, config):
                return await call_next(request)

        return JSONResponse(status_code=401, content={"detail": "Authentication required"})

    @staticmethod
    def _verify_token(token: str, config) -> bool:
        try:
            payload = jwt.decode(
                token, config.auth.jwt_secret, algorithms=[config.auth.jwt_algorithm]
            )
            return payload.get("exp", 0) > time.time()
        except jwt.PyJWTError:
            return False
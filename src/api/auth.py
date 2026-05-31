"""Paper trading API authentication dependency."""

import logging

from fastapi import HTTPException, Request

from src.config import get_config

logger = logging.getLogger(__name__)


async def verify_paper_token(request: Request) -> None:
    """Verify paper trading API token.

    Reads config.api.paper_token (env: AEGIS_PAPER_TOKEN).
    If not configured:
      - PRODUCTION: rejects with 401.
      - DEVELOPMENT / TEST: allows (dev mode, lifespan logs a one-time WARN).
    Otherwise, requires Authorization: Bearer <token> or X-Aegis-Token header.

    Raises:
        HTTPException 401: Missing token (production or token required).
        HTTPException 403: Invalid token.
    """
    config = get_config()
    token = getattr(config, "paper_token", "")
    profile = getattr(config, "profile", "DEVELOPMENT")
    profile_str = profile.upper() if hasattr(profile, "upper") else str(profile).upper()

    if not token:
        if profile_str == "PRODUCTION":
            logger.error("Paper API token missing in PRODUCTION; rejecting %s", request.url.path)
            raise HTTPException(status_code=401, detail="Paper trading token required (production)")
        # DEV / TEST: allow unauthenticated
        return

    # Check Authorization: Bearer <token>
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        if auth_header[7:] == token:
            return

    # Check X-Aegis-Token header
    aegis_token = request.headers.get("X-Aegis-Token", "")
    if aegis_token == token:
        return

    if not auth_header and not aegis_token:
        logger.warning("Paper API: missing auth token for %s", request.url.path)
        raise HTTPException(status_code=401, detail="Paper trading token required")

    logger.warning("Paper API: invalid auth token for %s", request.url.path)
    raise HTTPException(status_code=403, detail="Invalid paper trading token")

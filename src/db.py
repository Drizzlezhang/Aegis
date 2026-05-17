"""Database engine and session management."""

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.config import get_config

_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        config = get_config()
        url = config.database.url
        if url.startswith("sqlite"):
            url = url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
            # Expand ~ in path
            path_part = url.split(":///", 1)[1]
            url = url.replace(path_part, os.path.expanduser(path_part))
        elif url.startswith("postgresql"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        _engine = create_async_engine(
            url,
            pool_size=config.database.pool_size,
            max_overflow=config.database.max_overflow,
            echo=config.database.echo,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    async with factory() as session:
        yield session
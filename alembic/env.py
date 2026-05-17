"""Alembic env.py — configured for Aegis-Trader src.config."""

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_config as get_app_config

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def get_url() -> str:
    """Build async-compatible database URL from application config."""
    app_config = get_app_config()
    url = app_config.database.url
    if url.startswith("sqlite"):
        url = url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        # Expand ~ in path
        path_part = url.split(":///", 1)[1]
        expanded = os.path.expanduser(path_part)
        url = url.replace(path_part, expanded)
    elif url.startswith("postgresql"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = create_async_engine(get_url())

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
"""Root conftest.py — session-scoped DB initialization for all tests."""

import os

import pytest


@pytest.fixture(scope="session")
def _test_db_dir(tmp_path_factory):
    """Session-scoped temp directory for test database."""
    return tmp_path_factory.mktemp("aegis_test")


@pytest.fixture(scope="session", autouse=True)
def alembic_upgrade_head(_test_db_dir):
    """Run alembic upgrade head once per test session on a temp SQLite DB.

    Sets AEGIS_DATABASE__URL to a temp file, reloads config, runs migrations.
    This ensures all tests that access the DB (e.g. phase_history table)
    have the schema available.
    """
    db_path = _test_db_dir / "aegis.db"
    db_url = f"sqlite:///{db_path}"

    # Save original env var (if any) and set temp DB URL
    original_url = os.environ.get("AEGIS_DATABASE__URL")
    os.environ["AEGIS_DATABASE__URL"] = db_url

    # Reload config so get_config() returns the temp DB
    from src.config import reload_config
    reload_config()

    # Run migrations
    from alembic import command
    from alembic.config import Config as AlembicConfig

    alembic_cfg = AlembicConfig("alembic.ini")
    command.upgrade(alembic_cfg, "heads")

    yield

    # Restore original env var
    if original_url is not None:
        os.environ["AEGIS_DATABASE__URL"] = original_url
    else:
        del os.environ["AEGIS_DATABASE__URL"]
    reload_config()


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    """Inject AEGIS_DATA_DIR to a temp directory for the test duration."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("AEGIS_DATA_DIR", str(data_dir))
    return data_dir

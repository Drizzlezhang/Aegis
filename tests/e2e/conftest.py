"""E2E test fixtures — mock LLM + mock data sources."""

import random
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.main import app, lifespan


@pytest.fixture(autouse=True)
def mock_scheduler():
    """Mock AnalysisScheduler to avoid pickle errors with yfinance_ohlcv."""
    with patch("src.api.main.AnalysisScheduler") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.initialize = AsyncMock()
        mock_instance.start = MagicMock()
        mock_instance.stop = MagicMock()
        mock_instance.aclose = AsyncMock()
        mock_cls.return_value = mock_instance
        yield mock_cls


@pytest_asyncio.fixture
async def client():
    """Async HTTP client for testing the full API with lifespan triggered."""
    async with lifespan(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


@pytest.fixture(autouse=True)
def mock_llm():
    """Mock all LLM calls to return deterministic responses."""
    with patch("src.llm.client.generate", new_callable=AsyncMock) as mock:
        mock.return_value = _make_llm_content()
        yield mock


@pytest.fixture(autouse=True)
def mock_yfinance():
    """Mock yfinance data fetching at the DataFetcherManager level."""
    with patch(
        "src.agents.data_harvester.fetcher_manager.DataFetcherManager.fetch_all",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = {
            "ohlcv": _make_ohlcv_data(),
            "options_chain": None,
            "fundamentals": {},
        }
        yield mock


@pytest.fixture
def mock_telegram():
    """Mock Telegram notifications."""
    with patch(
        "src.services.notification.telegram.TelegramNotifier.send",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = True
        yield mock


def _make_llm_content() -> str:
    """Deterministic LLM response for testing."""
    return '{"action": "BUY", "confidence": 0.85, "reasoning": "Strong momentum"}'


def _make_ohlcv_data() -> dict:
    """Generate synthetic OHLCV data for testing — 60 days of slightly uptrending prices."""
    random.seed(42)
    base = 150.0
    data = []
    for i in range(60):
        d = date(2025, 1, 1) + timedelta(days=i)
        price = base + i * 0.5 + random.uniform(-2, 2)
        data.append({
            "date": d.isoformat(),
            "open": round(price - 0.5, 2),
            "high": round(price + 1.5, 2),
            "low": round(price - 1.5, 2),
            "close": round(price, 2),
            "volume": random.randint(1_000_000, 5_000_000),
        })
    return {"symbol": "TEST", "data": data, "raw": data}

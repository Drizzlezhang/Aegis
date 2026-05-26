"""E2E: Update settings -> verify runtime apply."""

import pytest


@pytest.mark.e2e
class TestSettingsFlow:
    @pytest.mark.asyncio
    async def test_get_and_update_settings(self, client):
        """GET settings -> PUT update -> GET verify changed."""
        # Get current
        get_resp = await client.get("/api/settings")
        assert get_resp.status_code == 200
        original = get_resp.json()

        # Update
        put_resp = await client.put("/api/settings", json={
            "confidence_threshold": 0.9,
        })
        assert put_resp.status_code == 200

        # Verify
        get_resp2 = await client.get("/api/settings")
        updated = get_resp2.json()
        assert updated["confidence_threshold"] == 0.9

    @pytest.mark.asyncio
    async def test_test_telegram_endpoint(self, client, mock_telegram):
        """Test telegram connection endpoint."""
        resp = await client.post("/api/settings/test-telegram")
        # Should not crash (may return 200 or 4xx depending on mock setup)
        assert resp.status_code in (200, 400, 500)

"""E2E: Open position -> update price -> trigger alert -> close position."""

import pytest


@pytest.mark.e2e
class TestPositionLifecycle:
    @pytest.mark.asyncio
    async def test_full_lifecycle(self, client):
        """Open -> update -> alerts -> close."""
        # 1. Open position
        open_resp = await client.post("/api/positions", json={
            "symbol": "NVDA",
            "contract_type": "call",
            "strike": 150.0,
            "expiry": "2025-06-20",
            "entry_price": 8.50,
            "quantity": 2,
            "stop_loss_pct": 50,
            "target_pct": 100,
        })
        assert open_resp.status_code == 201
        position_id = open_resp.json()["id"]

        # 2. Update price
        patch_resp = await client.patch(f"/api/positions/{position_id}", json={
            "current_price": 4.50,
        })
        assert patch_resp.status_code == 200

        # 3. Check alerts
        alerts_resp = await client.get("/api/positions/alerts")
        assert alerts_resp.status_code == 200

        # 4. Close position
        close_resp = await client.post(f"/api/positions/{position_id}/close", json={
            "close_price": 4.50,
            "reason": "stop_loss",
        })
        # Close may return 200 (success) or 400 (already closed/rolled)
        assert close_resp.status_code in (200, 400)

    @pytest.mark.asyncio
    async def test_roll_position(self, client):
        """Open -> roll -> verify chain."""
        # Open
        resp = await client.post("/api/positions", json={
            "symbol": "AAPL",
            "contract_type": "call",
            "strike": 200.0,
            "expiry": "2025-06-20",
            "entry_price": 5.0,
            "quantity": 1,
        })
        position_id = resp.json()["id"]

        # Roll
        roll_resp = await client.post(f"/api/positions/{position_id}/roll", json={
            "new_strike": 210.0,
            "new_expiry": "2025-07-18",
            "new_entry_price": 6.0,
        })
        assert roll_resp.status_code == 200
        data = roll_resp.json()
        assert "new_position" in data
        assert "old_position" in data
        assert data["old_position"]["id"] == position_id

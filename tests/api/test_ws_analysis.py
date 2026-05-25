"""Tests for WebSocket analysis progress endpoint."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect


class TestWSAnalysis:
    """Tests for /ws/analysis/{request_id} endpoint."""

    @pytest.mark.asyncio
    async def test_ws_connection_accepted(self):
        """WebSocket connection to analysis endpoint is accepted."""
        from fastapi import FastAPI, WebSocket
        from fastapi.testclient import TestClient

        app = FastAPI()
        orchestrator_mock = MagicMock()

        @app.websocket("/ws/analysis/{request_id}")
        async def ws_endpoint(websocket: WebSocket, request_id: str):
            await websocket.accept()
            await websocket.send_json({"type": "connected", "request_id": request_id})
            try:
                while True:
                    await websocket.receive_text()
            except WebSocketDisconnect:
                pass

        client = TestClient(app)
        with client.websocket_connect("/ws/analysis/test-123") as ws:
            data = ws.receive_json()
            assert data["type"] == "connected"
            assert data["request_id"] == "test-123"

    @pytest.mark.asyncio
    async def test_ws_receives_progress_events(self):
        """WebSocket receives pipeline_progress events from orchestrator."""
        from fastapi import FastAPI, WebSocket
        from fastapi.testclient import TestClient

        app = FastAPI()
        listeners: dict[str, list] = {}

        class MockOrchestrator:
            def add_listener(self, event_name, listener):
                listeners.setdefault(event_name, []).append(listener)

            def remove_listener(self, event_name, listener):
                lst = listeners.get(event_name, [])
                if listener in lst:
                    lst.remove(listener)

        orch = MockOrchestrator()

        @app.websocket("/ws/analysis/{request_id}")
        async def ws_endpoint(websocket: WebSocket, request_id: str):
            await websocket.accept()
            queue: asyncio.Queue = asyncio.Queue(maxsize=100)

            async def on_progress(**payload):
                if payload.get("request_id") == request_id:
                    queue.put_nowait(payload)

            orch.add_listener("pipeline_progress", on_progress)
            try:
                while True:
                    event = await queue.get()
                    await websocket.send_json(event)
            except WebSocketDisconnect:
                pass
            finally:
                orch.remove_listener("pipeline_progress", on_progress)

        client = TestClient(app)
        with client.websocket_connect("/ws/analysis/test-456") as ws:
            # Simulate orchestrator emitting a progress event
            for listener in listeners.get("pipeline_progress", []):
                await listener(
                    type="pipeline_progress",
                    request_id="test-456",
                    step={"index": 0, "total": 6, "agent": "Data-Harvester", "status": "started"},
                )

            data = ws.receive_json()
            assert data["type"] == "pipeline_progress"
            assert data["request_id"] == "test-456"
            assert data["step"]["agent"] == "Data-Harvester"
            assert data["step"]["status"] == "started"

    @pytest.mark.asyncio
    async def test_ws_filters_by_request_id(self):
        """Events with non-matching request_id are not forwarded."""
        from fastapi import FastAPI, WebSocket
        from fastapi.testclient import TestClient

        app = FastAPI()
        listeners: dict[str, list] = {}

        class MockOrchestrator:
            def add_listener(self, event_name, listener):
                listeners.setdefault(event_name, []).append(listener)

            def remove_listener(self, event_name, listener):
                lst = listeners.get(event_name, [])
                if listener in lst:
                    lst.remove(listener)

        orch = MockOrchestrator()

        @app.websocket("/ws/analysis/{request_id}")
        async def ws_endpoint(websocket: WebSocket, request_id: str):
            await websocket.accept()
            queue: asyncio.Queue = asyncio.Queue(maxsize=100)

            async def on_progress(**payload):
                if payload.get("request_id") == request_id:
                    queue.put_nowait(payload)

            orch.add_listener("pipeline_progress", on_progress)
            try:
                while True:
                    event = await queue.get()
                    await websocket.send_json(event)
            except WebSocketDisconnect:
                pass
            finally:
                orch.remove_listener("pipeline_progress", on_progress)

        client = TestClient(app)
        with client.websocket_connect("/ws/analysis/req-A") as ws:
            # Emit event for a different request_id
            for listener in listeners.get("pipeline_progress", []):
                await listener(
                    type="pipeline_progress",
                    request_id="req-B",
                    step={"index": 0, "total": 6, "agent": "Quant-Brain", "status": "started"},
                )
            # Emit matching event
            for listener in listeners.get("pipeline_progress", []):
                await listener(
                    type="pipeline_progress",
                    request_id="req-A",
                    step={"index": 0, "total": 6, "agent": "Data-Harvester", "status": "started"},
                )

            data = ws.receive_json()
            # Should receive only the matching event
            assert data["request_id"] == "req-A"
            assert data["step"]["agent"] == "Data-Harvester"
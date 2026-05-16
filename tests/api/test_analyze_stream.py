"""Tests for analyze stream API endpoint."""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


class FakeOrchestrator:
    """Lightweight orchestrator for SSE route tests."""

    def __init__(self) -> None:
        self.listeners: dict[str, list] = {
            "step_started": [],
            "step_completed": [],
            "pipeline_completed": [],
        }

    def add_listener(self, event_name: str, listener) -> None:
        self.listeners.setdefault(event_name, []).append(listener)

    def remove_listener(self, event_name: str, listener) -> None:
        self.listeners[event_name] = [item for item in self.listeners.get(event_name, []) if item != listener]

    async def analyze_symbols(self, symbols: list[str]):
        if any(symbol.upper() == "INVALID" for symbol in symbols):
            raise RuntimeError("invalid symbol")

        steps = ["Data-Harvester", "Quant-Brain", "Strategy-Execution", "Aegis-Memory"]
        states = []
        for symbol in symbols:
            state = SimpleNamespace(
                symbol=symbol,
                agent_sequence=[],
                current_step=0,
                total_steps=len(steps),
                recommended_options=[],
                action_report="ok",
            )

            for idx, step_name in enumerate(steps, start=1):
                step = SimpleNamespace(index=idx, total=len(steps), display_name=step_name)
                state.current_step = idx - 1
                for listener in self.listeners.get("step_started", []):
                    await listener(step=step, state=state)

                await asyncio.sleep(0.002)
                state.current_step = idx
                state.agent_sequence.append(step_name)
                for listener in self.listeners.get("step_completed", []):
                    await listener(step=step, state=state)

            for listener in self.listeners.get("pipeline_completed", []):
                await listener(state=state)

            states.append(state)

        return states


def _parse_sse_events(body: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for chunk in body.strip().split("\n\n"):
        if not chunk.strip():
            continue
        lines = chunk.split("\n")
        event_name = "message"
        data = "{}"
        for line in lines:
            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip()
            if line.startswith("data:"):
                data = line.split(":", 1)[1].strip()
        events.append((event_name, json.loads(data)))
    return events


class TestAnalyzeStream:
    """Tests for POST /api/analyze/stream."""

    def test_empty_symbols_returns_400(self) -> None:
        response = client.post("/api/analyze/stream", json={"symbols": []})
        assert response.status_code == 400
        assert response.json() == {"detail": "No symbols provided"}

    def test_returns_sse_headers_and_event_sequence(self) -> None:
        fake_orchestrator = FakeOrchestrator()
        with patch("src.api.routes.analyze_stream._orchestrator", fake_orchestrator):
            response = client.post("/api/analyze/stream", json={"symbols": ["QQQ"]})

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers.get("cache-control") == "no-cache"

        events = _parse_sse_events(response.text)
        names = [name for name, _ in events]

        assert names[0] == "start"
        assert "progress" in names
        assert "step" in names
        assert "result" in names
        assert names[-1] == "done"

        assert names.index("start") < names.index("progress")
        assert names.index("progress") < names.index("step")
        assert names.index("step") < names.index("result")
        assert names.index("result") < names.index("done")

        result_payload = next(payload for name, payload in events if name == "result")
        assert result_payload["result"]["executionTime"] > 0

    def test_invalid_symbol_emits_error_event(self) -> None:
        fake_orchestrator = FakeOrchestrator()
        with patch("src.api.routes.analyze_stream._orchestrator", fake_orchestrator):
            response = client.post("/api/analyze/stream", json={"symbols": ["INVALID"]})

        assert response.status_code == 200
        events = _parse_sse_events(response.text)
        names = [name for name, _ in events]

        assert names[0] == "start"
        assert "error" in names
        assert names[-1] == "error"

"""WebSocket endpoint for real-time LLM call events."""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.services.event_bus import LLMCallEvent, get_event_bus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/llm")
async def llm_stream(websocket: WebSocket) -> None:
    """Stream LLMCallEvent updates in real time (cost, tokens, latency)."""
    await websocket.accept()
    logger.info("LLM WS client connected")

    bus = get_event_bus()
    queue: asyncio.Queue[dict] = asyncio.Queue()

    async def on_llm_call(event: LLMCallEvent) -> None:
        await queue.put({
            "type": "llm_call",
            "request_id": event.request_id,
            "agent_name": event.agent_name,
            "provider": event.provider,
            "model": event.model,
            "input_tokens": event.input_tokens,
            "output_tokens": event.output_tokens,
            "cost_usd": event.cost_usd,
            "latency_ms": event.latency_ms,
            "cache_hit": event.cache_hit,
            "success": event.success,
            "error_msg": event.error_msg,
            "timestamp": event.timestamp.isoformat(),
        })

    handle = bus.subscribe("LLMCallEvent", on_llm_call)

    try:
        while True:
            data = await queue.get()
            await websocket.send_json(data)
    except WebSocketDisconnect:
        pass
    finally:
        bus.unsubscribe(handle)
        logger.info("LLM WS client disconnected")

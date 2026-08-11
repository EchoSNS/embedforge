"""
WebSocket manager — real-time stage progress updates to the frontend.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()

# Active connections per session
_connections: Dict[str, Set[WebSocket]] = {}


async def broadcast(session_id: str, message: Dict[str, Any]) -> None:
    """Send a message to all WebSocket clients subscribed to a session."""
    conns = _connections.get(session_id, set())
    dead: Set[WebSocket] = set()
    payload = json.dumps(message, default=str)

    for ws in conns:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)

    conns -= dead


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()

    if session_id not in _connections:
        _connections[session_id] = set()
    _connections[session_id].add(websocket)

    logger.info(f"WebSocket connected: session={session_id}")

    try:
        while True:
            # Keep connection alive; client can send pings or chat messages
            data = await websocket.receive_text()
            # Echo acknowledgment
            await websocket.send_text(json.dumps({"type": "ack", "received": data}))
    except WebSocketDisconnect:
        _connections[session_id].discard(websocket)
        logger.info(f"WebSocket disconnected: session={session_id}")

"""
WebSocket manager — real-time stage progress updates and LLM-powered chat.
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


async def _handle_chat(session_id: str, message: str, websocket: WebSocket) -> None:
    """Process a user chat message with LLM context from the active session."""
    try:
        from config.llm_config import get_llm
        from langchain_core.messages import HumanMessage, SystemMessage

        # Get session context if available
        context = ""
        try:
            from server.routes.workflow import _sessions
            state = _sessions.get(session_id)
            if state:
                context = (
                    f"Current stage: {state.stage.value}\n"
                    f"Board: {state.board_name}\n"
                    f"Requirements: {json.dumps(state.requirements, default=str)[:500]}\n"
                )
        except Exception:
            pass

        system = (
            "You are an embedded systems assistant for EmbedForge. "
            "Help the user understand the current pipeline stage, suggest improvements, "
            "or answer questions about their firmware requirements.\n"
            f"Session context:\n{context}"
        )

        llm = get_llm()
        response = llm.invoke([
            SystemMessage(content=system),
            HumanMessage(content=message),
        ])

        await websocket.send_text(json.dumps({
            "type": "chat_response",
            "content": response.content,
        }))
    except Exception as e:
        await websocket.send_text(json.dumps({
            "type": "chat_response",
            "content": f"Sorry, I couldn't process that: {str(e)[:100]}",
        }))


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()

    if session_id not in _connections:
        _connections[session_id] = set()
    _connections[session_id].add(websocket)

    logger.info(f"WebSocket connected: session={session_id}")

    try:
        while True:
            data = await websocket.receive_text()
            # Send typing indicator, then LLM response
            await websocket.send_text(json.dumps({"type": "typing"}))
            await _handle_chat(session_id, data, websocket)
    except WebSocketDisconnect:
        _connections[session_id].discard(websocket)
        logger.info(f"WebSocket disconnected: session={session_id}")

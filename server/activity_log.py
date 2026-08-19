"""
Activity Log — real-time event streaming for frontend consumption.

Provides an SSE (Server-Sent Events) stream and an in-memory log buffer
so the UI can show live progress during SDK scans, profile generation, etc.
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Dict, Optional

_MAX_BUFFER = 200


class LogLevel(str, Enum):
    INFO = "info"
    STEP = "step"
    WARN = "warn"
    ERROR = "error"
    AI = "ai"
    SUCCESS = "success"


@dataclass
class LogEntry:
    level: LogLevel
    message: str
    detail: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "message": self.message,
            "detail": self.detail,
            "timestamp": self.timestamp,
        }


class ActivityLog:
    """Thread-safe activity log with async SSE streaming."""

    def __init__(self) -> None:
        self._buffer: deque[LogEntry] = deque(maxlen=_MAX_BUFFER)
        self._subscribers: list[asyncio.Queue] = []
        self._lock = threading.Lock()

    def emit(self, level: LogLevel, message: str, detail: str = "") -> None:
        entry = LogEntry(level=level, message=message, detail=detail)
        with self._lock:
            self._buffer.append(entry)
            for q in self._subscribers:
                try:
                    q.put_nowait(entry)
                except (asyncio.QueueFull, RuntimeError):
                    pass

    def info(self, message: str, detail: str = "") -> None:
        self.emit(LogLevel.INFO, message, detail)

    def step(self, message: str, detail: str = "") -> None:
        self.emit(LogLevel.STEP, message, detail)

    def warn(self, message: str, detail: str = "") -> None:
        self.emit(LogLevel.WARN, message, detail)

    def error(self, message: str, detail: str = "") -> None:
        self.emit(LogLevel.ERROR, message, detail)

    def ai(self, message: str, detail: str = "") -> None:
        self.emit(LogLevel.AI, message, detail)

    def success(self, message: str, detail: str = "") -> None:
        self.emit(LogLevel.SUCCESS, message, detail)

    def get_recent(self, count: int = 50) -> list[Dict[str, Any]]:
        entries = list(self._buffer)[-count:]
        return [e.to_dict() for e in entries]

    def get_buffer(self) -> list[LogEntry]:
        """Return all buffered log entries."""
        return list(self._buffer)

    async def subscribe(self) -> AsyncGenerator[str, None]:
        """Yield SSE-formatted log entries as they arrive."""
        q: asyncio.Queue[LogEntry] = asyncio.Queue(maxsize=100)
        self._subscribers.append(q)
        try:
            while True:
                entry = await q.get()
                yield f"data: {json.dumps(entry.to_dict())}\n\n"
        finally:
            self._subscribers.remove(q)


# Singleton
activity_log = ActivityLog()

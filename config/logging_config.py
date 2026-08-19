"""
Structured Logging — JSON-formatted log output with session correlation IDs.
"""

from __future__ import annotations

import json
import logging
import sys
import threading
from contextvars import ContextVar
from typing import Optional

session_id_var: ContextVar[str] = ContextVar("session_id", default="")


class StructuredFormatter(logging.Formatter):
    """JSON log formatter with session correlation."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        sid = session_id_var.get("")
        if sid:
            log_entry["session_id"] = sid

        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def configure_logging(level: str = "INFO", structured: bool = True) -> None:
    """Configure root logger with structured or plain formatting."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    if structured:
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s (%(session_id)s) — %(message)s",
            defaults={"session_id": ""},
        ))
    root.addHandler(handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


class SessionLogContext:
    """Context manager that sets the session ID for the current async/thread context."""

    def __init__(self, session_id: str) -> None:
        self._sid = session_id
        self._token = None

    def __enter__(self):
        self._token = session_id_var.set(self._sid)
        return self

    def __exit__(self, *_):
        if self._token:
            session_id_var.reset(self._token)

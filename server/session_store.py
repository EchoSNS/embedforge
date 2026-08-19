"""
Session Store — SQLite-backed persistence for workflow sessions.

Survives server restarts. Uses JSON serialization of WorkflowState.
Falls back to in-memory dict if SQLite init fails.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from dataclasses import asdict, fields
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).resolve().parent.parent / "sessions.db"


def _init_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            state_json TEXT NOT NULL,
            stage TEXT NOT NULL,
            board_name TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at)")
    conn.commit()
    return conn


class SessionStore:
    """Thread-safe SQLite-backed session store with dict-like interface."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._lock = threading.Lock()
        self._path = db_path or _DB_PATH
        try:
            self._conn = _init_db(self._path)
            self._enabled = True
            logger.info("Session store initialized: %s", self._path)
        except Exception as e:
            logger.warning("SQLite session store unavailable, using in-memory: %s", e)
            self._conn = None
            self._enabled = False
        self._cache: Dict[str, Any] = {}

    def _serialize(self, state) -> str:
        d = asdict(state)
        d["stage"] = state.stage.value
        # snapshots can contain complex nested data
        return json.dumps(d, default=str)

    def _deserialize(self, json_str: str):
        from core.workflow import WorkflowState, WorkflowStage
        d = json.loads(json_str)
        stage_value = d.pop("stage", "init")
        d.pop("snapshots", None)
        state = WorkflowState(**{
            k: v for k, v in d.items()
            if k in {f.name for f in fields(WorkflowState)}
        })
        state.stage = WorkflowStage(stage_value)
        return state

    def __setitem__(self, session_id: str, state) -> None:
        self._cache[session_id] = state
        if not self._enabled:
            return
        try:
            now = datetime.utcnow().isoformat()
            with self._lock:
                self._conn.execute(
                    """INSERT OR REPLACE INTO sessions
                       (session_id, state_json, stage, board_name, created_at, updated_at)
                       VALUES (?, ?, ?, ?, COALESCE((SELECT created_at FROM sessions WHERE session_id = ?), ?), ?)""",
                    (session_id, self._serialize(state), state.stage.value,
                     state.board_name, session_id, now, now),
                )
                self._conn.commit()
        except Exception as e:
            logger.warning("Failed to persist session %s: %s", session_id, e)

    def __getitem__(self, session_id: str):
        if session_id in self._cache:
            return self._cache[session_id]
        if not self._enabled:
            raise KeyError(session_id)
        try:
            with self._lock:
                row = self._conn.execute(
                    "SELECT state_json FROM sessions WHERE session_id = ?",
                    (session_id,),
                ).fetchone()
            if row:
                state = self._deserialize(row[0])
                self._cache[session_id] = state
                return state
        except Exception as e:
            logger.warning("Failed to load session %s: %s", session_id, e)
        raise KeyError(session_id)

    def __contains__(self, session_id: str) -> bool:
        if session_id in self._cache:
            return True
        if not self._enabled:
            return False
        try:
            with self._lock:
                row = self._conn.execute(
                    "SELECT 1 FROM sessions WHERE session_id = ?",
                    (session_id,),
                ).fetchone()
            return row is not None
        except Exception:
            return False

    def get(self, session_id: str, default=None):
        try:
            return self[session_id]
        except KeyError:
            return default

    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent sessions metadata (without full state)."""
        if not self._enabled:
            return [
                {"session_id": sid, "stage": s.stage.value, "board_name": s.board_name, "created_at": s.created_at}
                for sid, s in self._cache.items()
            ]
        try:
            with self._lock:
                rows = self._conn.execute(
                    "SELECT session_id, stage, board_name, created_at, updated_at FROM sessions ORDER BY updated_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [
                {"session_id": r[0], "stage": r[1], "board_name": r[2], "created_at": r[3], "updated_at": r[4]}
                for r in rows
            ]
        except Exception:
            return []

    def close(self) -> None:
        if self._conn:
            self._conn.close()

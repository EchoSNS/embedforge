"""
Cost Tracker — monitors LLM token usage and estimated spend per session/stage.

Uses LangChain callbacks to intercept token counts from every LLM call.
Reads actual token data from response_metadata/usage_metadata (provider-reported),
falling back to the built-in pricing table for cost estimation.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

logger = logging.getLogger(__name__)

_COST_DB_PATH = Path(__file__).resolve().parent.parent / "cost_data.db"


# Pricing per 1M tokens (input/output) — update as models change
_MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "gpt-4": {"input": 30.0, "output": 60.0},
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4.1": {"input": 2.0, "output": 8.0},
    "gpt-4.1-mini": {"input": 0.4, "output": 1.6},
    "gpt-4.1-nano": {"input": 0.1, "output": 0.4},
    "gpt-5": {"input": 2.0, "output": 8.0},
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
}

_DEFAULT_PRICING = {"input": 5.0, "output": 15.0}


def _load_pricing_overrides() -> Dict[str, Dict[str, float]]:
    """Load pricing overrides from EMBEDFORGE_COST_OVERRIDES env var (JSON)."""
    raw = os.getenv("EMBEDFORGE_COST_OVERRIDES", "")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def get_model_pricing() -> Dict[str, Dict[str, float]]:
    """Return the effective pricing table (base + env overrides)."""
    merged = dict(_MODEL_PRICING)
    merged.update(_load_pricing_overrides())
    return merged


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = get_model_pricing().get(model, _DEFAULT_PRICING)
    return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000


def _parse_budget() -> Optional[float]:
    raw = os.getenv("EMBEDFORGE_BUDGET_USD", "")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


@dataclass
class LLMCallRecord:
    """Single LLM invocation record."""

    timestamp: float
    session_id: str
    stage: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    duration_ms: float


@dataclass
class SessionCostSummary:
    """Aggregated cost data for a session."""

    session_id: str
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    call_count: int = 0
    by_stage: Dict[str, Dict[str, Any]] = field(default_factory=lambda: defaultdict(lambda: {
        "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "calls": 0,
    }))


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = _MODEL_PRICING.get(model, _DEFAULT_PRICING)
    return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000


class CostTracker:
    """Thread-safe singleton that accumulates LLM cost data across all sessions.
    Persists to SQLite so cost history survives server restarts."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: List[LLMCallRecord] = []
        self._sessions: Dict[str, SessionCostSummary] = {}
        self._budget_usd: Optional[float] = _parse_budget()
        self._budget_callbacks: List[Any] = []
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()
        self._load_from_db()

    def _init_db(self) -> None:
        try:
            self._conn = sqlite3.connect(str(_COST_DB_PATH), check_same_thread=False)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS llm_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    session_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    model TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    cost_usd REAL NOT NULL,
                    duration_ms REAL NOT NULL
                )
            """)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            self._conn.commit()
            # Restore budget from DB
            row = self._conn.execute("SELECT value FROM config WHERE key='budget_usd'").fetchone()
            if row and self._budget_usd is None:
                try:
                    self._budget_usd = float(row[0])
                except ValueError:
                    pass
            logger.info("Cost tracker DB initialized: %s", _COST_DB_PATH)
        except Exception as e:
            logger.warning("Cost tracker DB init failed, running in-memory only: %s", e)
            self._conn = None

    def _load_from_db(self) -> None:
        if not self._conn:
            return
        try:
            rows = self._conn.execute(
                "SELECT timestamp, session_id, stage, model, input_tokens, output_tokens, cost_usd, duration_ms FROM llm_calls ORDER BY timestamp"
            ).fetchall()
            for r in rows:
                record = LLMCallRecord(
                    timestamp=r[0], session_id=r[1], stage=r[2], model=r[3],
                    input_tokens=r[4], output_tokens=r[5],
                    total_tokens=r[4] + r[5], cost_usd=r[6], duration_ms=r[7],
                )
                self._records.append(record)
                summary = self._sessions.setdefault(r[1], SessionCostSummary(session_id=r[1]))
                summary.total_input_tokens += r[4]
                summary.total_output_tokens += r[5]
                summary.total_cost_usd += r[6]
                summary.call_count += 1
                stage_data = summary.by_stage[r[2]]
                stage_data["input_tokens"] += r[4]
                stage_data["output_tokens"] += r[5]
                stage_data["cost_usd"] += r[6]
                stage_data["calls"] += 1
            if rows:
                logger.info("Loaded %d historical cost records from DB", len(rows))
        except Exception as e:
            logger.warning("Failed to load cost history: %s", e)

    def _persist_record(self, record: LLMCallRecord) -> None:
        if not self._conn:
            return
        try:
            self._conn.execute(
                "INSERT INTO llm_calls (timestamp, session_id, stage, model, input_tokens, output_tokens, cost_usd, duration_ms) VALUES (?,?,?,?,?,?,?,?)",
                (record.timestamp, record.session_id, record.stage, record.model,
                 record.input_tokens, record.output_tokens, record.cost_usd, record.duration_ms),
            )
            self._conn.commit()
        except Exception:
            pass

    def on_budget_exceeded(self, callback) -> None:
        self._budget_callbacks.append(callback)

    @property
    def budget_usd(self) -> Optional[float]:
        return self._budget_usd

    @budget_usd.setter
    def budget_usd(self, value: Optional[float]) -> None:
        self._budget_usd = value
        if self._conn:
            try:
                self._conn.execute(
                    "INSERT OR REPLACE INTO config (key, value) VALUES ('budget_usd', ?)",
                    (str(value) if value is not None else "",)
                )
                self._conn.commit()
            except Exception:
                pass

    def record_call(
        self,
        session_id: str,
        stage: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        duration_ms: float,
    ) -> LLMCallRecord:
        cost = _estimate_cost(model, input_tokens, output_tokens)
        record = LLMCallRecord(
            timestamp=time.time(),
            session_id=session_id,
            stage=stage,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=cost,
            duration_ms=duration_ms,
        )

        with self._lock:
            self._records.append(record)
            summary = self._sessions.setdefault(session_id, SessionCostSummary(session_id=session_id))
            summary.total_input_tokens += input_tokens
            summary.total_output_tokens += output_tokens
            summary.total_cost_usd += cost
            summary.call_count += 1

            stage_data = summary.by_stage[stage]
            stage_data["input_tokens"] += input_tokens
            stage_data["output_tokens"] += output_tokens
            stage_data["cost_usd"] += cost
            stage_data["calls"] += 1

            # Budget alert check
            if self._budget_usd is not None:
                total_spent = sum(s.total_cost_usd for s in self._sessions.values())
                if total_spent >= self._budget_usd:
                    for cb in self._budget_callbacks:
                        try:
                            cb(total_spent, self._budget_usd)
                        except Exception:
                            pass

        self._persist_record(record)
        return record

    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            s = self._sessions.get(session_id)
            if not s:
                return None
            return {
                "session_id": s.session_id,
                "total_input_tokens": s.total_input_tokens,
                "total_output_tokens": s.total_output_tokens,
                "total_cost_usd": round(s.total_cost_usd, 6),
                "call_count": s.call_count,
                "by_stage": dict(s.by_stage),
            }

    def get_global_summary(self) -> Dict[str, Any]:
        with self._lock:
            total_cost = sum(s.total_cost_usd for s in self._sessions.values())
            total_calls = sum(s.call_count for s in self._sessions.values())
            total_input = sum(s.total_input_tokens for s in self._sessions.values())
            total_output = sum(s.total_output_tokens for s in self._sessions.values())
            return {
                "total_cost_usd": round(total_cost, 6),
                "total_calls": total_calls,
                "total_input_tokens": total_input,
                "total_output_tokens": total_output,
                "session_count": len(self._sessions),
                "recent_calls": [
                    {
                        "session_id": r.session_id,
                        "stage": r.stage,
                        "model": r.model,
                        "tokens": r.total_tokens,
                        "cost_usd": round(r.cost_usd, 6),
                        "duration_ms": round(r.duration_ms, 1),
                        "timestamp": r.timestamp,
                    }
                    for r in self._records[-20:]
                ],
            }

    def get_recent_calls(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "session_id": r.session_id,
                    "stage": r.stage,
                    "model": r.model,
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "cost_usd": round(r.cost_usd, 6),
                    "duration_ms": round(r.duration_ms, 1),
                    "timestamp": r.timestamp,
                }
                for r in self._records[-limit:]
            ]

    def get_time_series(self, bucket_minutes: int = 60) -> List[Dict[str, Any]]:
        """Aggregate records into time buckets for charting."""
        from datetime import datetime, timezone
        with self._lock:
            if not self._records:
                return []

            buckets: Dict[int, Dict[str, Any]] = {}
            bucket_sec = bucket_minutes * 60

            for r in self._records:
                key = int(r.timestamp // bucket_sec) * bucket_sec
                if key not in buckets:
                    buckets[key] = {
                        "timestamp": key,
                        "cost_usd": 0.0,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "calls": 0,
                        "by_stage": defaultdict(float),
                    }
                b = buckets[key]
                b["cost_usd"] += r.cost_usd
                b["input_tokens"] += r.input_tokens
                b["output_tokens"] += r.output_tokens
                b["calls"] += 1
                b["by_stage"][r.stage] += r.cost_usd

            result = []
            for key in sorted(buckets):
                b = buckets[key]
                result.append({
                    "timestamp": b["timestamp"],
                    "label": datetime.fromtimestamp(b["timestamp"], tz=timezone.utc).strftime("%H:%M"),
                    "cost_usd": round(b["cost_usd"], 6),
                    "input_tokens": b["input_tokens"],
                    "output_tokens": b["output_tokens"],
                    "calls": b["calls"],
                    "by_stage": dict(b["by_stage"]),
                })
            return result

    def get_stage_totals(self) -> List[Dict[str, Any]]:
        """Per-stage totals across all sessions for pie/bar charts."""
        with self._lock:
            stage_agg: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
                "cost_usd": 0.0, "input_tokens": 0, "output_tokens": 0,
                "calls": 0, "avg_duration_ms": 0.0, "_durations": [],
            })
            for r in self._records:
                s = stage_agg[r.stage]
                s["cost_usd"] += r.cost_usd
                s["input_tokens"] += r.input_tokens
                s["output_tokens"] += r.output_tokens
                s["calls"] += 1
                s["_durations"].append(r.duration_ms)

            result = []
            for stage, s in sorted(stage_agg.items()):
                durations = s.pop("_durations")
                s["avg_duration_ms"] = round(sum(durations) / len(durations), 1) if durations else 0
                s["cost_usd"] = round(s["cost_usd"], 6)
                result.append({"stage": stage, **s})
            return result

    def get_budget_status(self) -> Dict[str, Any]:
        with self._lock:
            total_spent = sum(s.total_cost_usd for s in self._sessions.values())
            return {
                "budget_usd": self._budget_usd,
                "spent_usd": round(total_spent, 6),
                "remaining_usd": round(self._budget_usd - total_spent, 6) if self._budget_usd else None,
                "percent_used": round((total_spent / self._budget_usd) * 100, 1) if self._budget_usd else None,
                "exceeded": total_spent >= self._budget_usd if self._budget_usd else False,
            }


# Singleton
cost_tracker = CostTracker()


class CostTrackingCallback(BaseCallbackHandler):
    """LangChain callback that records token usage to the CostTracker."""

    def __init__(self, session_id: str = "unknown", stage: str = "unknown") -> None:
        self.session_id = session_id
        self.stage = stage
        self._start_time: Optional[float] = None

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> None:
        self._start_time = time.time()

    def on_chat_model_start(self, serialized: Dict[str, Any], messages: List, **kwargs: Any) -> None:
        self._start_time = time.time()

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        duration_ms = (time.time() - (self._start_time or time.time())) * 1000

        input_tokens = 0
        output_tokens = 0
        model = ""

        # Source 1: LangChain usage_metadata on the generation (modern path)
        if response.generations:
            for gen_list in response.generations:
                for gen in gen_list:
                    msg = getattr(gen, "message", None)
                    if msg:
                        usage = getattr(msg, "usage_metadata", None)
                        if usage:
                            input_tokens = usage.get("input_tokens", 0)
                            output_tokens = usage.get("output_tokens", 0)
                        resp_meta = getattr(msg, "response_metadata", {})
                        if resp_meta:
                            model = model or resp_meta.get("model_name", "") or resp_meta.get("model", "")

        # Source 2: llm_output.token_usage (OpenAI/Azure classic path)
        if not (input_tokens or output_tokens):
            token_usage = response.llm_output.get("token_usage", {}) if response.llm_output else {}
            input_tokens = token_usage.get("prompt_tokens", 0)
            output_tokens = token_usage.get("completion_tokens", 0)

        if not model and response.llm_output:
            model = response.llm_output.get("model_name", "") or response.llm_output.get("model", "")

        if input_tokens or output_tokens:
            cost_tracker.record_call(
                session_id=self.session_id,
                stage=self.stage,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=duration_ms,
            )

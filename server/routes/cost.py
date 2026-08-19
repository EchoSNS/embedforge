"""
Cost API routes — expose LLM usage and spending data to the frontend.
"""

from __future__ import annotations

from fastapi import APIRouter

from core.cost_tracker import cost_tracker, get_model_pricing

router = APIRouter()


@router.get("/summary")
async def global_summary():
    """Global cost summary across all sessions."""
    return cost_tracker.get_global_summary()


@router.get("/session/{session_id}")
async def session_cost(session_id: str):
    """Cost breakdown for a specific session."""
    summary = cost_tracker.get_session_summary(session_id)
    if not summary:
        return {"session_id": session_id, "total_cost_usd": 0, "call_count": 0, "by_stage": {}}
    return summary


@router.get("/recent")
async def recent_calls(limit: int = 50):
    """Recent LLM calls with token/cost details."""
    return cost_tracker.get_recent_calls(min(limit, 200))


@router.get("/pricing")
async def pricing_table():
    """Return the effective pricing table (base + env overrides per 1M tokens)."""
    return get_model_pricing()

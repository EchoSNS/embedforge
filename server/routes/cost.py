"""
Cost API routes — expose LLM usage and spending data to the frontend.
"""

from __future__ import annotations

from typing import Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel

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


@router.get("/metrics")
async def metrics(bucket_minutes: int = 60):
    """Time-series cost data bucketed for charting."""
    return {
        "time_series": cost_tracker.get_time_series(max(1, min(bucket_minutes, 1440))),
        "stage_totals": cost_tracker.get_stage_totals(),
        "budget": cost_tracker.get_budget_status(),
    }


class BudgetUpdate(BaseModel):
    budget_usd: Optional[float] = None


@router.put("/budget")
async def set_budget(req: BudgetUpdate):
    """Set or clear the spending budget (in-memory, resets on restart)."""
    cost_tracker.budget_usd = req.budget_usd
    return cost_tracker.get_budget_status()


@router.get("/cache")
async def cache_stats():
    """LLM response cache hit/miss statistics."""
    from core.llm_cache import llm_cache
    return llm_cache.stats()


@router.delete("/cache")
async def clear_cache():
    """Clear the LLM response cache."""
    from core.llm_cache import llm_cache
    llm_cache.clear()
    return {"status": "cleared"}


@router.get("/stage-models")
async def get_stage_model_config():
    """Return current stage→model mapping and the default model."""
    from config.settings import get_stage_models, ALL_STAGES, AppSettings
    from config.llm_config import LLMSettings

    settings = LLMSettings.from_env()
    overrides = get_stage_models()

    stages = {}
    for stage in ALL_STAGES:
        stages[stage] = overrides.get(stage, None)

    return {
        "default_model": settings.model,
        "provider": settings.provider,
        "stages": stages,
    }


class StageModelsUpdate(BaseModel):
    stages: Dict[str, Optional[str]]


@router.put("/stage-models")
async def update_stage_models(req: StageModelsUpdate):
    """Update stage→model mapping at runtime."""
    from config.settings import set_stage_models, ALL_STAGES

    cleaned = {k: v for k, v in req.stages.items() if k in ALL_STAGES and v}
    set_stage_models(cleaned)
    return await get_stage_model_config()

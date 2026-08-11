"""
Workflow API routes — start, approve, edit, regenerate pipeline stages.
"""

from __future__ import annotations

import io
import json
import zipfile
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.workflow import WorkflowEngine, WorkflowStage, WorkflowState
from server.main import get_registry
from server.ws import broadcast

router = APIRouter()

# In-memory session store (swap for Redis/DB in production)
_sessions: Dict[str, WorkflowState] = {}


class StartRequest(BaseModel):
    user_input: str
    board_name: str


class EditRequest(BaseModel):
    data: Dict[str, Any]


class ChatMessage(BaseModel):
    message: str


@router.post("/start")
async def start_workflow(req: StartRequest):
    registry = get_registry()
    engine = WorkflowEngine(registry)
    state = engine.initialize_state(req.user_input, req.board_name)
    _sessions[state.session_id] = state
    return {"session_id": state.session_id, "stage": state.stage.value}


@router.get("/{session_id}/state")
async def get_state(session_id: str):
    state = _get_session(session_id)
    return _serialize_state(state)


@router.post("/{session_id}/approve/{stage}")
async def approve_stage(session_id: str, stage: str):
    state = _get_session(session_id)
    registry = get_registry()
    engine = WorkflowEngine(registry)

    await broadcast(session_id, {"type": "stage_start", "stage": stage})

    try:
        if stage == "refiner" or state.stage == WorkflowStage.CLARIFIER:
            state = engine.run_refiner(state)
        elif stage == "hardware" or state.stage == WorkflowStage.HARDWARE:
            state = engine.run_hardware(state)
        elif stage == "software_arch" or state.stage == WorkflowStage.SOFTWARE_ARCH:
            state = engine.run_software_arch(state)
        elif stage == "software_detailed" or state.stage == WorkflowStage.SOFTWARE_DETAILED:
            state = engine.run_software_detailed(state)
        elif stage == "codegen" or state.stage == WorkflowStage.CODEGEN:
            state = engine.run_codegen(state)
        elif stage == "review" or state.stage == WorkflowStage.REVIEW:
            state = engine.run_review(state)
        else:
            raise HTTPException(400, f"Unknown stage: {stage}")
    except Exception as e:
        await broadcast(session_id, {"type": "error", "message": str(e)})
        raise HTTPException(500, str(e))

    _sessions[session_id] = state
    payload = _serialize_state(state)
    await broadcast(session_id, {"type": "stage_complete", **payload})
    return payload


@router.post("/{session_id}/edit/{stage}")
async def edit_stage(session_id: str, stage: str, req: EditRequest):
    state = _get_session(session_id)

    if stage == "requirements":
        state.requirements = req.data
    elif stage == "hardware":
        state.hardware_spec = req.data
    elif stage == "software_arch":
        state.software_arch = req.data
    elif stage == "software_detailed":
        state.software_detailed = req.data
    else:
        raise HTTPException(400, f"Cannot edit stage: {stage}")

    _sessions[session_id] = state
    return {"ok": True}


@router.get("/{session_id}/download")
async def download_code(session_id: str):
    from fastapi.responses import StreamingResponse

    state = _get_session(session_id)
    if not state.generated_code:
        raise HTTPException(404, "No generated code available")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in state.generated_code.items():
            zf.writestr(name, content)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=embedforge_output.zip"},
    )


def _get_session(session_id: str) -> WorkflowState:
    if session_id not in _sessions:
        raise HTTPException(404, f"Session '{session_id}' not found")
    return _sessions[session_id]


def _serialize_state(state: WorkflowState) -> Dict[str, Any]:
    return {
        "session_id": state.session_id,
        "stage": state.stage.value,
        "user_input": state.user_input,
        "board_name": state.board_name,
        "requirements": state.requirements,
        "hardware_spec": state.hardware_spec,
        "software_arch": state.software_arch,
        "software_detailed": state.software_detailed,
        "generated_code": state.generated_code,
        "review_result": state.review_result,
        "errors": state.errors,
        "history": state.history,
    }

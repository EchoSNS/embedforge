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
    from server.activity_log import activity_log

    registry = get_registry()
    engine = WorkflowEngine(registry)

    activity_log.step("New session started", f"Board: {req.board_name}")
    activity_log.info("Initializing workflow state…")
    state = engine.initialize_state(req.user_input, req.board_name)

    activity_log.ai("Auto-refining requirements…", f"Input: {req.user_input[:80]}")
    try:
        state = engine.run_refiner(state)
        activity_log.success("Requirements refined successfully")
    except Exception as e:
        activity_log.error("Refiner failed", str(e)[:200])
        state.errors.append(f"Refiner failed: {e}")

    _sessions[state.session_id] = state
    await broadcast(state.session_id, {"type": "stage_complete", "stage": "refiner"})
    return {"session_id": state.session_id, "stage": state.stage.value}


@router.get("/{session_id}/state")
async def get_state(session_id: str):
    state = _get_session(session_id)
    return _serialize_state(state)


@router.post("/{session_id}/approve/{stage}")
async def approve_stage(session_id: str, stage: str):
    from server.activity_log import activity_log

    state = _get_session(session_id)
    registry = get_registry()
    engine = WorkflowEngine(registry)

    stage_labels = {
        "refiner": "Requirements Refinement",
        "hardware": "Hardware Design",
        "software_arch": "Software Architecture",
        "software_detailed": "Detailed Design",
        "codegen": "Code Generation",
        "review": "AI Review",
    }
    activity_log.step(f"Stage approved: {stage_labels.get(stage, stage)}", f"Session: {session_id[:8]}")
    await broadcast(session_id, {"type": "stage_start", "stage": stage})

    try:
        if stage == "refiner" or state.stage == WorkflowStage.CLARIFIER:
            activity_log.ai("AI is refining requirements…")
            state = engine.run_refiner(state)
        elif stage == "hardware" or state.stage == WorkflowStage.HARDWARE:
            activity_log.ai("AI is assigning peripherals and pins…")
            state = engine.run_hardware(state)
        elif stage == "software_arch" or state.stage == WorkflowStage.SOFTWARE_ARCH:
            activity_log.ai("AI is selecting SDK drivers…")
            state = engine.run_software_arch(state)
        elif stage == "software_detailed" or state.stage == WorkflowStage.SOFTWARE_DETAILED:
            activity_log.ai("AI is creating function-level design…")
            state = engine.run_software_detailed(state)
        elif stage == "codegen" or state.stage == WorkflowStage.CODEGEN:
            activity_log.ai("AI is generating C code via TDD pipeline…")
            state = engine.run_codegen(state)
        elif stage == "review" or state.stage == WorkflowStage.REVIEW:
            activity_log.ai("AI is reviewing generated code…")
            state = engine.run_review(state)
        else:
            raise HTTPException(400, f"Unknown stage: {stage}")

        activity_log.success(f"Stage complete: {stage_labels.get(stage, stage)}")
    except Exception as e:
        activity_log.error(f"Stage failed: {stage}", str(e)[:200])
        await broadcast(session_id, {"type": "error", "message": str(e)})
        raise HTTPException(500, str(e))

    _sessions[session_id] = state
    payload = _serialize_state(state)
    await broadcast(session_id, {"type": "stage_complete", **payload})
    return payload


@router.post("/{session_id}/edit/{stage}")
async def edit_stage(session_id: str, stage: str, req: EditRequest):
    state = _get_session(session_id)

    # Accept both stage names and data key names from frontend
    stage_map = {
        "requirements": "requirements",
        "hardware": "hardware_spec",
        "hardware_spec": "hardware_spec",
        "software_arch": "software_arch",
        "software_architecture": "software_arch",
        "software_detailed": "software_detailed",
    }

    target = stage_map.get(stage)
    if not target:
        raise HTTPException(400, f"Cannot edit stage: {stage}")

    setattr(state, target, req.data)
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


@router.post("/{session_id}/validate")
async def validate_code(session_id: str):
    """Run code validation (pins, includes, rules) without compilation."""
    from core.code_validator import CodeValidator

    state = _get_session(session_id)
    if not state.generated_code:
        raise HTTPException(400, "No generated code to validate")

    registry = get_registry()
    validator = CodeValidator(registry)
    report = validator.validate(state.generated_code)

    return {
        "passed": report.passed,
        "errors": report.errors,
        "warnings": report.warnings,
        "pin_issues": report.pin_issues,
        "missing_headers": report.missing_headers,
        "rule_violations": report.rule_violations,
    }


@router.post("/{session_id}/build")
async def build_code(session_id: str):
    """Attempt to compile generated code using the plugin's compiler backend."""
    from services.build_service import BuildRequest, LocalBuildService

    state = _get_session(session_id)
    if not state.generated_code:
        raise HTTPException(400, "No generated code to build")

    registry = get_registry()
    build_svc = LocalBuildService(registry)

    if not build_svc.is_available():
        return {"success": False, "log": "Compiler toolchain not available on this machine"}

    request = BuildRequest(
        source_files=state.generated_code,
        board_name=state.board_name,
    )
    response = build_svc.build(request)

    state.build_result = {
        "success": response.success,
        "log": response.log,
    }
    _sessions[session_id] = state

    await broadcast(session_id, {"type": "build_complete", "success": response.success})
    return {"success": response.success, "log": response.log}


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

"""
Workflow API routes — start, approve, edit, regenerate pipeline stages.
"""

from __future__ import annotations

import io
import json
import logging
import zipfile
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.workflow import WorkflowEngine, WorkflowStage, WorkflowState
from server.main import get_registry
from server.ws import broadcast

logger = logging.getLogger(__name__)
router = APIRouter()

from server.session_store import SessionStore
_sessions = SessionStore()


class StartRequest(BaseModel):
    user_input: str
    board_name: str


class EditRequest(BaseModel):
    data: Dict[str, Any]


class ChatMessage(BaseModel):
    message: str


@router.post("/start")
async def start_workflow(req: StartRequest):
    from config.logging_config import SessionLogContext
    from server.activity_log import activity_log

    registry = get_registry()
    engine = WorkflowEngine(registry)

    activity_log.step("New session started", f"Board: {req.board_name}")
    activity_log.info("Initializing workflow state…")
    state = engine.initialize_state(req.user_input, req.board_name)

    with SessionLogContext(state.session_id):
        logger.info("Starting workflow: board=%s, input=%s", req.board_name, req.user_input[:80])
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


@router.get("/sessions/list")
async def list_sessions(limit: int = 50):
    """Return recent sessions metadata."""
    return _sessions.list_sessions(min(limit, 200))


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Delete a session from the store."""
    if session_id in _sessions:
        del _sessions[session_id]
    return {"status": "deleted"}


@router.get("/{session_id}/state")
async def get_state(session_id: str):
    state = _get_session(session_id)
    return _serialize_state(state)


@router.post("/{session_id}/approve/{stage}")
async def approve_stage(session_id: str, stage: str):
    from server.activity_log import activity_log

    logger.info("Stage approval: session=%s, stage=%s", session_id, stage)
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

    state.save_snapshot()

    # Clear previous errors on retry
    if state.errors:
        logger.info("Clearing %d previous error(s) for retry", len(state.errors))
        state.errors = []

    def _run_stage():
        """Execute the blocking LLM stage in a thread so SSE stays live."""
        nonlocal state
        if stage == "refiner" or state.stage == WorkflowStage.CLARIFIER:
            activity_log.ai("AI is refining requirements…")
            return engine.run_refiner(state)
        elif stage == "hardware" or state.stage == WorkflowStage.HARDWARE:
            activity_log.ai("AI is assigning peripherals and pins…")
            return engine.run_hardware(state)
        elif stage == "software_arch" or state.stage == WorkflowStage.SOFTWARE_ARCH:
            activity_log.ai("AI is selecting SDK drivers…")
            return engine.run_software_arch(state)
        elif stage == "software_detailed" or state.stage == WorkflowStage.SOFTWARE_DETAILED:
            activity_log.ai("AI is creating function-level design…")
            return engine.run_software_detailed(state)
        elif stage == "codegen" or state.stage == WorkflowStage.CODEGEN:
            activity_log.ai("AI is generating C code via TDD pipeline…")
            return engine.run_codegen(state)
        elif stage == "review" or state.stage == WorkflowStage.REVIEW:
            activity_log.ai("AI is reviewing generated code…")
            return engine.run_review(state)
        else:
            raise HTTPException(400, f"Unknown stage: {stage}")

    try:
        import asyncio
        state = await asyncio.to_thread(_run_stage)
        activity_log.success(f"Stage complete: {stage_labels.get(stage, stage)}")
    except HTTPException:
        raise
    except Exception as e:
        activity_log.error(f"Stage failed: {stage}", str(e)[:200])
        await broadcast(session_id, {"type": "error", "message": str(e)})
        raise HTTPException(500, str(e))

    _sessions[session_id] = state
    payload = _serialize_state(state)

    if state.errors:
        activity_log.error(
            f"Stage completed with errors: {stage_labels.get(stage, stage)}",
            "; ".join(state.errors[:3]),
        )
        await broadcast(session_id, {"type": "stage_error", **payload})
    else:
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


@router.post("/{session_id}/rollback/{target_stage}")
async def rollback_stage(session_id: str, target_stage: str):
    """Rollback workflow to a previous stage, clearing subsequent outputs."""
    from server.activity_log import activity_log

    state = _get_session(session_id)
    if state.rollback_to(target_stage):
        _sessions[session_id] = state
        activity_log.step(f"Rolled back to {target_stage}", f"Session: {session_id[:8]}")
        await broadcast(session_id, {"type": "stage_rollback", "stage": target_stage})
        return _serialize_state(state)
    raise HTTPException(400, f"Cannot rollback to '{target_stage}' from current stage '{state.stage.value}'")


@router.get("/{session_id}/download")
async def download_code(session_id: str, include_build: bool = False):
    from fastapi.responses import StreamingResponse

    state = _get_session(session_id)
    if not state.generated_code:
        raise HTTPException(404, "No generated code available")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in state.generated_code.items():
            zf.writestr(name, content)

        if include_build:
            from core.build_templates import generate_cmake, generate_makefile
            registry = get_registry()
            source_files = [n for n in state.generated_code if n.endswith(".c")]
            try:
                board = registry.get_board_template(state.board_name)
                inc_paths = board.get_sdk_include_paths()
                mcu = board.get_config().mcu
            except Exception:
                inc_paths, mcu = [], ""

            zf.writestr("CMakeLists.txt", generate_cmake("firmware", source_files, mcu, inc_paths))
            zf.writestr("Makefile", generate_makefile("firmware", source_files, mcu, inc_paths))

    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=embedforge_output.zip"},
    )


@router.get("/{session_id}/download/stage/{stage}")
async def download_stage(session_id: str, stage: str):
    """Download a single stage's data as JSON."""
    from fastapi.responses import Response

    state = _get_session(session_id)
    stage_data_map = {
        "requirements": state.requirements,
        "hardware": state.hardware_spec,
        "hardware_spec": state.hardware_spec,
        "software_arch": state.software_arch,
        "software_architecture": state.software_arch,
        "software_detailed": state.software_detailed,
        "codegen": state.generated_code,
        "generated_code": state.generated_code,
        "review": state.review_result,
        "review_result": state.review_result,
        "build": state.build_result,
        "build_result": state.build_result,
    }

    data = stage_data_map.get(stage)
    if data is None:
        raise HTTPException(400, f"Unknown stage: {stage}")
    if not data:
        raise HTTPException(404, f"No data for stage: {stage}")

    content = json.dumps(data, indent=2, default=str)
    filename = f"embedforge_{stage}.json"

    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{session_id}/download/full")
async def download_full_package(session_id: str):
    """Download complete package: all stage data, generated code, and logs."""
    from fastapi.responses import StreamingResponse
    from server.activity_log import activity_log

    state = _get_session(session_id)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Stage data
        zf.writestr("stages/requirements.json", json.dumps(state.requirements, indent=2, default=str))
        zf.writestr("stages/hardware_spec.json", json.dumps(state.hardware_spec, indent=2, default=str))
        zf.writestr("stages/software_arch.json", json.dumps(state.software_arch, indent=2, default=str))
        zf.writestr("stages/software_detailed.json", json.dumps(state.software_detailed, indent=2, default=str))
        zf.writestr("stages/review_result.json", json.dumps(state.review_result, indent=2, default=str))
        zf.writestr("stages/build_result.json", json.dumps(state.build_result, indent=2, default=str))

        # Generated source files
        for name, content in state.generated_code.items():
            zf.writestr(f"src/{name}", content)

        # Activity logs
        logs = activity_log.get_buffer()
        log_lines = [
            f"[{entry.timestamp:.3f}] [{entry.level.value}] {entry.message}"
            + (f" | {entry.detail}" if entry.detail else "")
            for entry in logs
        ]
        zf.writestr("logs/activity.log", "\n".join(log_lines))

        # Session metadata
        meta = {
            "session_id": state.session_id,
            "board_name": state.board_name,
            "user_input": state.user_input,
            "stage": state.stage.value,
            "created_at": state.created_at,
            "errors": state.errors,
        }
        zf.writestr("metadata.json", json.dumps(meta, indent=2, default=str))

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=embedforge_full_{session_id[:8]}.zip"},
    )


@router.post("/{session_id}/validate")
async def validate_code(session_id: str):
    """Run code validation (pins, includes, rules) without compilation."""
    from core.code_validator import CodeValidator

    logger.info("Validation requested for session %s", session_id)
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
        "static_analysis_issues": report.static_analysis_issues,
    }


@router.post("/{session_id}/analyze")
async def analyze_code(session_id: str):
    """Run cppcheck static analysis on generated code."""
    from core.static_analyzer import StaticAnalyzer
    from server.activity_log import activity_log

    state = _get_session(session_id)
    if not state.generated_code:
        raise HTTPException(400, "No generated code to analyze")

    analyzer = StaticAnalyzer()
    if not analyzer.is_available():
        logger.warning("Static analysis requested but cppcheck not installed")
        return {"available": False, "message": "cppcheck not installed"}

    activity_log.step("Running static analysis…", f"Session: {session_id[:8]}")
    logger.info("Static analysis requested for session %s", session_id)
    result = analyzer.analyze(state.generated_code)

    if result.has_critical:
        activity_log.error("Static analysis found critical issues", f"{result.errors} error(s)")
    elif result.total_issues > 0:
        activity_log.warn("Static analysis found issues", f"{result.total_issues} issue(s)")
    else:
        activity_log.success("Static analysis passed — no issues found")

    await broadcast(session_id, {"type": "analysis_complete", "issues": result.total_issues})

    return {
        "success": result.success,
        "total_issues": result.total_issues,
        "errors": result.errors,
        "warnings": result.warnings,
        "style": result.style,
        "performance": result.performance,
        "portability": result.portability,
        "issues": [
            {
                "file": i.file,
                "line": i.line,
                "severity": i.severity,
                "message": i.message,
                "id": i.issue_id,
            }
            for i in result.issues
        ],
    }


@router.post("/{session_id}/build")
async def build_code(session_id: str):
    """Attempt to compile generated code using the plugin's compiler backend."""
    from services.build_service import BuildRequest, LocalBuildService

    logger.info("Build requested for session %s", session_id)
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
        "build_result": state.build_result,
        "errors": state.errors,
        "history": state.history,
    }

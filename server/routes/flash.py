"""
Flash API routes — probe discovery, firmware flashing, and target reset.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.flash_service import PyOCDFlashService

logger = logging.getLogger(__name__)
router = APIRouter()

_flash_svc = PyOCDFlashService()


class FlashRequest(BaseModel):
    binary_path: str
    target: str = ""
    probe_id: Optional[str] = None


class ResetRequest(BaseModel):
    target: str = ""
    probe_id: Optional[str] = None


@router.get("/status")
async def flash_status():
    """Check if the flash service is available."""
    info = _flash_svc.get_info()
    logger.debug("Flash service status requested: %s", info)
    return info


@router.get("/probes")
async def list_probes():
    """Discover connected debug probes."""
    if not _flash_svc.is_available():
        logger.warning("Probe listing requested but pyOCD not installed")
        return {"probes": [], "message": "pyOCD not installed. Run: pip install pyocd"}

    probes = _flash_svc.list_probes()
    logger.info("Probe discovery returned %d probe(s)", len(probes))
    return {
        "probes": [
            {
                "unique_id": p.unique_id,
                "vendor": p.vendor,
                "product": p.product,
            }
            for p in probes
        ]
    }


@router.post("/program")
async def flash_firmware(req: FlashRequest):
    """Flash a compiled binary to the target MCU."""
    from server.activity_log import activity_log

    if not _flash_svc.is_available():
        logger.error("Flash requested but pyOCD not installed")
        raise HTTPException(503, "pyOCD not installed. Run: pip install pyocd")

    activity_log.step("Flashing firmware…", f"Binary: {req.binary_path}")
    logger.info("Flash request: binary=%s target=%s probe=%s", req.binary_path, req.target, req.probe_id)

    result = _flash_svc.flash(
        binary_path=req.binary_path,
        target=req.target,
        probe_id=req.probe_id,
    )

    if result.success:
        activity_log.success("Firmware flashed successfully", f"{result.duration_seconds}s")
    else:
        activity_log.error("Flash failed", result.message)

    return {
        "success": result.success,
        "message": result.message,
        "bytes_programmed": result.bytes_programmed,
        "duration_seconds": result.duration_seconds,
    }


@router.post("/reset")
async def reset_target(req: ResetRequest):
    """Reset the target MCU."""
    if not _flash_svc.is_available():
        logger.error("Reset requested but pyOCD not installed")
        raise HTTPException(503, "pyOCD not installed")

    logger.info("Target reset request: target=%s probe=%s", req.target, req.probe_id)
    success = _flash_svc.reset(target=req.target, probe_id=req.probe_id)

    if not success:
        raise HTTPException(500, "Target reset failed")

    return {"success": True, "message": "Target reset successful"}

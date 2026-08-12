"""
SDK Management API — scan SDKs, generate/edit capability profiles, analyze references.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List

import yaml
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from core.profile_generator import ProfileGenerator
from core.reference_analyzer import ReferenceProjectAnalyzer
from core.sdk_analyzer import SDKAnalyzer
from server.activity_log import activity_log as log

router = APIRouter()


def _get_registry():
    from server.main import get_registry
    return get_registry()


# ─── Request/Response Models ────────────────────────────────────────────────


class SdkScanRequest(BaseModel):
    path: str
    max_depth: int = 5


class ProfileGenerateRequest(BaseModel):
    sdk_path: str
    vendor_name: str = ""
    sdk_name: str = ""


class ProfileUpdateRequest(BaseModel):
    profile: Dict[str, Any]


class ReferenceAnalyzeRequest(BaseModel):
    path: str


# ─── SDK Scanning ───────────────────────────────────────────────────────────


@router.post("/scan")
async def scan_sdk(req: SdkScanRequest):
    """Scan SDK headers at the given path and return extracted metadata."""
    sdk_path = Path(req.path)
    log.step("SDK Scan started", f"Path: {req.path}")

    if not sdk_path.exists():
        log.error("Path not found", req.path)
        raise HTTPException(404, f"Path not found: {req.path}")

    # Count files first
    h_files = list(sdk_path.rglob("*.h"))
    c_files = list(sdk_path.rglob("*.c"))
    log.info(f"Found {len(h_files)} header files and {len(c_files)} source files")

    if not h_files and not c_files:
        log.warn("No .h or .c files found in this directory")
        return {
            "headers_scanned": 0, "functions_count": 0, "types_count": 0,
            "macros_count": 0, "functions": [], "types": [],
            "peripherals_detected": [],
            "message": "No .h or .c files found. Point to a directory containing C header files.",
        }

    t0 = time.time()
    analyzer = SDKAnalyzer(include_paths=[req.path])
    log.info("Parsing header files…")
    result = analyzer.analyze()
    elapsed = time.time() - t0

    peripherals = _detect_peripherals(result.functions)

    log.success(
        f"Scan complete in {elapsed:.1f}s",
        f"{result.headers_scanned} headers · {len(result.functions)} functions · "
        f"{len(result.types)} types · {len(result.macros)} macros",
    )

    if peripherals:
        log.info(f"Detected peripherals: {', '.join(peripherals)}")
    else:
        log.warn("No peripheral patterns detected in function names")

    return {
        "headers_scanned": result.headers_scanned,
        "functions_count": len(result.functions),
        "types_count": len(result.types),
        "macros_count": len(result.macros),
        "functions": [
            {"name": f.name, "return_type": f.return_type, "parameters": f.parameters, "header": f.header_file}
            for f in result.functions[:200]
        ],
        "types": [
            {"name": t.name, "kind": t.kind, "header": t.header_file}
            for t in result.types[:100]
        ],
        "peripherals_detected": peripherals,
    }


# ─── Profile Generation ────────────────────────────────────────────────────


@router.post("/generate-profile")
async def generate_profile(req: ProfileGenerateRequest):
    """Auto-generate a capability profile from an SDK scan using LLM assistance."""
    sdk_path = Path(req.sdk_path)
    if not sdk_path.exists():
        log.error("SDK path not found", req.sdk_path)
        raise HTTPException(404, f"SDK path not found: {req.sdk_path}")

    log.step("Profile generation started", f"Vendor: {req.vendor_name or '(auto-detect)'}, SDK: {req.sdk_name or '(auto-detect)'}")
    log.info("Scanning SDK headers for function signatures…")

    generator = ProfileGenerator()
    t0 = time.time()

    try:
        profile_data = await generator.generate(
            sdk_path=req.sdk_path,
            vendor_name=req.vendor_name,
            sdk_name=req.sdk_name,
        )
        elapsed = time.time() - t0

        periph_count = len(profile_data.get("peripherals", {}))
        log.success(f"Profile generated in {elapsed:.1f}s", f"{periph_count} peripherals detected")
        return {"profile": profile_data, "status": "generated"}

    except Exception as e:
        log.error("Profile generation failed", str(e))
        raise HTTPException(500, str(e))


@router.get("/profile")
async def get_active_profile():
    """Get the currently active plugin's capability profile."""
    registry = _get_registry()
    profile = registry.get_capability_profile()
    if not profile:
        return {"profile": None, "status": "no_profile"}

    return {
        "profile": {
            "vendor": profile.vendor,
            "sdk": profile.sdk,
            "sdk_version": profile.sdk_version,
            "supported_families": profile.supported_families,
            "peripherals": profile.peripherals,
            "patterns": profile.patterns,
            "constraints": profile.constraints,
            "clock_tree": profile.clock_tree,
        },
        "reference_snippets": list(profile.reference_snippets.keys()),
        "status": "active",
    }


@router.put("/profile")
async def update_profile(req: ProfileUpdateRequest):
    """Update the active plugin's capability profile."""
    log.step("Saving profile changes…")
    registry = _get_registry()
    manifest = registry._require_active()
    plugin_dir = Path(__file__).resolve().parent.parent.parent / "plugins" / manifest.name

    profile_path = plugin_dir / "profile.yaml"
    profile_path.write_text(yaml.dump(req.profile, default_flow_style=False, sort_keys=False))

    cache_key = f"__profile__{manifest.name}"
    registry._instances.pop(cache_key, None)

    log.success("Profile saved", str(profile_path))
    return {"status": "updated"}


# ─── Reference Analysis ─────────────────────────────────────────────────────


@router.post("/reference/analyze")
async def analyze_reference(req: ReferenceAnalyzeRequest):
    """Analyze a reference C project at the given path."""
    ref_path = Path(req.path)
    if not ref_path.exists():
        log.error("Reference path not found", req.path)
        raise HTTPException(404, f"Path not found: {req.path}")

    log.step("Reference analysis started", f"Path: {req.path}")
    t0 = time.time()

    analyzer = ReferenceProjectAnalyzer()
    result = analyzer.analyze(req.path)
    elapsed = time.time() - t0

    log.success(
        f"Analysis complete in {elapsed:.1f}s",
        f"{result.files_analyzed} files · {len(result.functions_defined)} functions · "
        f"{len(result.functions_called)} SDK calls",
    )

    return {
        "files_analyzed": result.files_analyzed,
        "includes": result.includes[:50],
        "functions_defined": [
            {"name": f.name, "return_type": f.return_type, "file": f.file}
            for f in result.functions_defined[:100]
        ],
        "functions_called": result.functions_called[:100],
        "peripherals_used": result.peripherals_used,
        "patterns": result.patterns,
    }


@router.post("/reference/upload")
async def upload_reference(files: List[UploadFile] = File(...)):
    """Upload reference C/H files for analysis."""
    filenames = [f.filename for f in files if f.filename]
    log.step(f"Uploading {len(files)} reference files", ", ".join(filenames[:5]))

    analyzer = ReferenceProjectAnalyzer()
    file_contents: Dict[str, str] = {}

    for f in files:
        if f.filename and (f.filename.endswith(".c") or f.filename.endswith(".h")):
            content = await f.read()
            file_contents[f.filename] = content.decode("utf-8", errors="ignore")
            log.info(f"Read {f.filename}", f"{len(content)} bytes")

    if not file_contents:
        log.warn("No valid .c or .h files in upload")
        raise HTTPException(400, "No valid .c or .h files uploaded")

    result = analyzer.analyze_files(file_contents)
    log.success(f"Upload analysis complete", f"{result.files_analyzed} files parsed")

    return {
        "files_analyzed": result.files_analyzed,
        "includes": result.includes,
        "functions_defined": [
            {"name": f.name, "return_type": f.return_type, "file": f.file}
            for f in result.functions_defined
        ],
        "functions_called": result.functions_called,
        "peripherals_used": result.peripherals_used,
        "patterns": result.patterns,
    }


# ─── Helpers ────────────────────────────────────────────────────────────────


def _detect_peripherals(functions) -> List[str]:
    """Heuristic: detect peripheral types from function naming patterns."""
    peripheral_keywords = {
        "PWM": ["pwm", "tim_pwm", "timer_pwm"],
        "ADC": ["adc"],
        "UART": ["uart", "usart"],
        "SPI": ["spi"],
        "I2C": ["i2c"],
        "GPIO": ["gpio"],
        "DMA": ["dma"],
        "CAN": ["can"],
        "DAC": ["dac"],
        "RTC": ["rtc"],
        "WDG": ["wdg", "iwdg", "wwdg"],
        "TIMER": ["tim_base", "tim_ic", "tim_oc"],
    }
    found = set()
    for fn in functions:
        name_lower = fn.name.lower()
        for peripheral, keywords in peripheral_keywords.items():
            if any(kw in name_lower for kw in keywords):
                found.add(peripheral)
    return sorted(found)

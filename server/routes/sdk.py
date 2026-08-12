"""
SDK Management API — scan SDKs, generate/edit capability profiles, analyze references.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from core.profile_generator import ProfileGenerator
from core.reference_analyzer import ReferenceProjectAnalyzer
from core.sdk_analyzer import SDKAnalyzer

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
    if not sdk_path.exists():
        raise HTTPException(404, f"Path not found: {req.path}")

    analyzer = SDKAnalyzer(include_paths=[req.path])
    result = analyzer.analyze()

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
        "peripherals_detected": _detect_peripherals(result.functions),
    }


# ─── Profile Generation ────────────────────────────────────────────────────


@router.post("/generate-profile")
async def generate_profile(req: ProfileGenerateRequest):
    """Auto-generate a capability profile from an SDK scan using LLM assistance."""
    sdk_path = Path(req.sdk_path)
    if not sdk_path.exists():
        raise HTTPException(404, f"SDK path not found: {req.sdk_path}")

    generator = ProfileGenerator()
    profile_data = await generator.generate(
        sdk_path=req.sdk_path,
        vendor_name=req.vendor_name,
        sdk_name=req.sdk_name,
    )

    return {"profile": profile_data, "status": "generated"}


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
    registry = _get_registry()
    manifest = registry._require_active()
    plugin_dir = Path(__file__).resolve().parent.parent.parent / "plugins" / manifest.name

    profile_path = plugin_dir / "profile.yaml"
    profile_path.write_text(yaml.dump(req.profile, default_flow_style=False, sort_keys=False))

    # Clear cached profile so next access reloads
    cache_key = f"__profile__{manifest.name}"
    registry._instances.pop(cache_key, None)

    return {"status": "updated"}


# ─── Reference Analysis ─────────────────────────────────────────────────────


@router.post("/reference/analyze")
async def analyze_reference(req: ReferenceAnalyzeRequest):
    """Analyze a reference C project at the given path."""
    ref_path = Path(req.path)
    if not ref_path.exists():
        raise HTTPException(404, f"Path not found: {req.path}")

    analyzer = ReferenceProjectAnalyzer()
    result = analyzer.analyze(req.path)

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
    analyzer = ReferenceProjectAnalyzer()
    file_contents: Dict[str, str] = {}

    for f in files:
        if f.filename and (f.filename.endswith(".c") or f.filename.endswith(".h")):
            content = await f.read()
            file_contents[f.filename] = content.decode("utf-8", errors="ignore")

    if not file_contents:
        raise HTTPException(400, "No valid .c or .h files uploaded")

    result = analyzer.analyze_files(file_contents)

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

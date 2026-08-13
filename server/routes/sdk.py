"""
SDK Management API — scan SDKs, generate/edit capability profiles, analyze references.
"""

from __future__ import annotations

import json
import re
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


class ProfileSaveRequest(BaseModel):
    name: str
    profile: Dict[str, Any]


class ReferenceAnalyzeRequest(BaseModel):
    path: str
    profile_name: str = ""


_PROFILES_DIR = Path(__file__).resolve().parent.parent.parent / "profiles"


def _ensure_profiles_dir() -> Path:
    _PROFILES_DIR.mkdir(exist_ok=True)
    return _PROFILES_DIR


def _sanitize_profile_name(profile_name: str) -> str:
    """Validate profile name as a single safe path component."""
    if not profile_name:
        raise HTTPException(400, "Profile name is required")
    if profile_name in {".", ".."}:
        raise HTTPException(400, "Invalid profile name")
    if "/" in profile_name or "\\" in profile_name:
        raise HTTPException(400, "Invalid profile name")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", profile_name):
        raise HTTPException(400, "Invalid profile name")
    return profile_name


def _sanitize_filename(filename: str) -> str:
    """Validate filename as a single safe path component."""
    if not filename:
        raise HTTPException(400, "Filename is required")
    if filename in {".", ".."}:
        raise HTTPException(400, "Invalid filename")
    if "/" in filename or "\\" in filename:
        raise HTTPException(400, "Invalid filename")
    return filename


def _refs_dir_for(profile_name: str) -> Path:
    """Get the references directory for a specific profile."""
    safe_profile_name = _sanitize_profile_name(profile_name)
    refs_root = (_ensure_profiles_dir() / "references").resolve()
    d = (refs_root / safe_profile_name).resolve()
    try:
        d.relative_to(refs_root)
    except ValueError:
        d.relative_to(refs_root)
    except ValueError:
        raise HTTPException(400, "Invalid profile name")
    d.mkdir(parents=True, exist_ok=True)
    return d


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

        # Auto-save to library
        vendor_slug = (req.vendor_name or "unknown").lower().replace(" ", "_")
        sdk_slug = (req.sdk_name or "sdk").lower().replace(" ", "_")
        profiles_dir = _ensure_profiles_dir()
        auto_name = f"{vendor_slug}_{sdk_slug}"
        (profiles_dir / f"{auto_name}.yaml").write_text(
            yaml.dump(profile_data, default_flow_style=False, sort_keys=False)
        )
        log.info(f"Auto-saved to library as {auto_name}.yaml")

        return {"profile": profile_data, "status": "generated", "saved_as": f"{auto_name}.yaml"}

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


# ─── Profile Library ────────────────────────────────────────────────────────


@router.get("/profiles")
async def list_profiles():
    """List all saved profiles in the library."""
    profiles_dir = _ensure_profiles_dir()
    refs_base = profiles_dir / "references"
    profiles = []
    for f in sorted(profiles_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(f.read_text())
            name_stem = f.stem
            ref_count = len(list((refs_base / name_stem).glob("*.json"))) if (refs_base / name_stem).exists() else 0
            profiles.append({
                "filename": f.name,
                "vendor": data.get("vendor", "Unknown"),
                "sdk": data.get("sdk", "Unknown"),
                "sdk_version": data.get("sdk_version", ""),
                "peripherals_count": len(data.get("peripherals", {})),
                "references_count": ref_count,
            })
        except Exception:
            profiles.append({"filename": f.name, "vendor": "Error", "sdk": "Could not parse"})
    return profiles


@router.post("/profiles/save")
async def save_profile(req: ProfileSaveRequest):
    """Save a profile to the library."""
    profiles_dir = _ensure_profiles_dir()
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in req.name)
    filepath = profiles_dir / f"{safe_name}.yaml"
    filepath.write_text(yaml.dump(req.profile, default_flow_style=False, sort_keys=False))
    log.success(f"Profile saved to library: {safe_name}")
    return {"status": "saved", "filename": filepath.name}


@router.post("/profiles/activate/{filename}")
async def activate_profile(filename: str):
    """Copy a library profile to the active plugin's profile.yaml."""
    profiles_dir = _ensure_profiles_dir()
    source = profiles_dir / filename
    if not source.exists():
        raise HTTPException(404, f"Profile not found: {filename}")

    registry = _get_registry()
    manifest = registry._require_active()
    plugin_dir = Path(__file__).resolve().parent.parent.parent / "plugins" / manifest.name
    target = plugin_dir / "profile.yaml"

    target.write_text(source.read_text())
    cache_key = f"__profile__{manifest.name}"
    registry._instances.pop(cache_key, None)

    log.success(f"Activated profile: {filename}")
    return {"status": "activated"}


@router.delete("/profiles/{filename}")
async def delete_profile(filename: str):
    """Delete a profile from the library."""
    safe_filename = _sanitize_filename(filename)
    profiles_dir = _ensure_profiles_dir().resolve()
    filepath = (profiles_dir / safe_filename).resolve()
    if profiles_dir != filepath.parent and profiles_dir not in filepath.parents:
        raise HTTPException(400, "Invalid profile filename")
    if not filepath.exists():
        raise HTTPException(404, f"Profile not found: {filename}")
    filepath.unlink()
    log.info(f"Deleted profile: {filename}")
    return {"status": "deleted"}


# ─── Reference Analysis (profile-scoped) ────────────────────────────────────


@router.post("/reference/analyze")
async def analyze_reference(req: ReferenceAnalyzeRequest):
    """Analyze a reference C project and optionally tie it to a profile."""
    ref_path = Path(req.path)
    if not ref_path.exists():
        log.error("Reference path not found", req.path)
        raise HTTPException(404, f"Path not found: {req.path}")

    log.step("Reference analysis started", f"Path: {req.path}")
    t0 = time.time()

    analyzer = ReferenceProjectAnalyzer()
    result = analyzer.analyze(req.path)
    elapsed = time.time() - t0

    analysis_data = {
        "files_analyzed": result.files_analyzed,
        "includes": result.includes[:50],
        "functions_defined": [
            {"name": f.name, "return_type": f.return_type, "file": f.file}
            for f in result.functions_defined[:100]
        ],
        "functions_called": result.functions_called[:100],
        "peripherals_used": result.peripherals_used,
        "patterns": result.patterns,
        "source_path": req.path,
    }

    # Save to profile if specified
    if req.profile_name:
        refs_dir = _refs_dir_for(req.profile_name)
        raw_slug = Path(req.path).name or "reference"
        slug = re.sub(r"[^A-Za-z0-9._-]", "_", raw_slug).strip("._-") or "reference"
        filepath = refs_dir / f"{slug}.json"

        refs_root = refs_dir.resolve()
        resolved_filepath = filepath.resolve()
        if refs_root != resolved_filepath.parent and refs_root not in resolved_filepath.parents:
            raise HTTPException(400, "Invalid reference filename")

        resolved_filepath.write_text(json.dumps(analysis_data, indent=2))
        log.info(f"Reference saved to profile: {req.profile_name}/{slug}")
        analysis_data["saved_to"] = f"{req.profile_name}/{resolved_filepath.name}"

    log.success(
        f"Analysis complete in {elapsed:.1f}s",
        f"{result.files_analyzed} files · {len(result.functions_defined)} functions",
    )
    return analysis_data


@router.post("/reference/upload")
async def upload_reference(files: List[UploadFile] = File(...), profile_name: str = ""):
    """Upload reference C/H files for analysis, optionally tied to a profile."""
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

    analysis_data = {
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

    if profile_name:
        refs_dir = _refs_dir_for(profile_name).resolve()
        filepath = (refs_dir / "uploaded.json").resolve()
        try:
            filepath.relative_to(refs_dir)
        except ValueError:
            raise HTTPException(400, "Invalid profile path")
        filepath.write_text(json.dumps(analysis_data, indent=2))
        log.info(f"Upload reference saved to profile: {profile_name}")
        analysis_data["saved_to"] = f"{profile_name}/uploaded.json"

    log.success(f"Upload analysis complete", f"{result.files_analyzed} files parsed")
    return analysis_data


@router.get("/reference/{profile_name}")
async def get_profile_references(profile_name: str):
    """Get all reference analyses tied to a specific profile."""
    refs_dir = _refs_dir_for(profile_name)
    references = []
    for f in sorted(refs_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            references.append({
                "filename": f.name,
                "files_analyzed": data.get("files_analyzed", 0),
                "functions_count": len(data.get("functions_defined", [])),
                "source_path": data.get("source_path", "uploaded"),
            })
        except Exception:
            pass
    return references


@router.delete("/reference/{profile_name}/{filename}")
async def delete_profile_reference(profile_name: str, filename: str):
    """Remove a reference analysis from a profile."""
    refs_dir = _refs_dir_for(profile_name).resolve()
    try:
        filepath.relative_to(refs_dir)
    except ValueError:
    filepath = (refs_dir / safe_filename).resolve()
    if refs_dir != filepath.parent and refs_dir not in filepath.parents:
        raise HTTPException(400, "Invalid reference filename")
    if not filepath.exists():
        raise HTTPException(404, f"Reference not found: {filename}")
    filepath.unlink()
    log.info(f"Deleted reference {filename} from profile {profile_name}")
    return {"status": "deleted"}


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

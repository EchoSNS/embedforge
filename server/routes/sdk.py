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
    refs_root.mkdir(parents=True, exist_ok=True)

    d = (refs_root / safe_profile_name).resolve()

    try:
        d.relative_to(refs_root)
    except ValueError:
        raise HTTPException(400, "Invalid profile name")
    d.mkdir(parents=True, exist_ok=True)
    return d


# ─── SDK Scanning ───────────────────────────────────────────────────────────


@router.post("/scan")
async def scan_sdk(req: SdkScanRequest):
    """Scan SDK headers at the given path and return extracted metadata."""
    from config.settings import AppSettings
    settings = AppSettings()

    sdk_path = Path(req.path).resolve()

    if settings.allowed_sdk_roots:
        allowed = any(
            sdk_path == Path(root).resolve() or Path(root).resolve() in sdk_path.parents
            for root in settings.allowed_sdk_roots
        )
        if not allowed:
            raise HTTPException(403, "Path is outside allowed SDK directories. Configure EMBEDFORGE_SDK_ROOTS.")

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
        vendor_slug = re.sub(r"[^a-z0-9_-]", "_", (req.vendor_name or "unknown").lower())
        sdk_slug = re.sub(r"[^a-z0-9_-]", "_", (req.sdk_name or "sdk").lower())
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
    safe_filename = _sanitize_filename(filename)
    profiles_dir = _ensure_profiles_dir().resolve()
    source = (profiles_dir / safe_filename).resolve()
    try:
        source.relative_to(profiles_dir)
    except ValueError:
        raise HTTPException(400, "Invalid profile filename")
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

        refs_root = refs_dir.resolve(strict=False)
        resolved_filepath = filepath.resolve(strict=False)
        try:
            resolved_filepath.relative_to(refs_root)
        except ValueError:
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
    safe_filename = _sanitize_filename(filename)
    filepath = (refs_dir / safe_filename).resolve()
    try:
        filepath.relative_to(refs_dir)
    except ValueError:
        raise HTTPException(400, "Invalid reference filename")
    if not filepath.exists():
        raise HTTPException(404, f"Reference not found: {filename}")
    filepath.unlink()
    log.info(f"Deleted reference {filename} from profile {profile_name}")
    return {"status": "deleted"}


# ─── Device Data Import ─────────────────────────────────────────────────────


class DeviceImportRequest(BaseModel):
    path: str
    device_name: str = ""


@router.post("/device/import")
async def import_device_data(req: DeviceImportRequest):
    """Import device hardware data (pin-mux, peripherals, registers) from vendor tools."""
    from core.device_db import get_device_db
    from core.importers.cubemx_importer import CubeMXImporter
    from core.importers.svd_parser import SVDParser
    from core.importers.cmsis_pack_importer import CMSISPackImporter
    from core.importers.atdf_importer import ATDFImporter
    from core.importers.illd_pin_extractor import ILLDPinExtractor

    importers = [CubeMXImporter(), ILLDPinExtractor(), ATDFImporter(), SVDParser(), CMSISPackImporter()]

    # Find a compatible importer
    importer = None
    for imp in importers:
        if imp.can_import(req.path):
            importer = imp
            break

    if importer is None:
        raise HTTPException(400, "No compatible importer found. Supported: CubeMX XML, SVD, CMSIS-Pack (.pack), Microchip ATDF.")

    log.step("Importing device data…", f"Source: {req.path}")

    info = importer.import_device(req.path, req.device_name)
    if info is None:
        raise HTTPException(500, "Failed to parse device data from the given path.")

    db = get_device_db()
    device_id = db.import_device(info)

    log.success(
        f"Imported {info.device} ({info.package})",
        f"{len(info.pin_mux)} pin-mux entries, {len(info.peripherals)} peripherals"
    )

    return {
        "device_id": device_id,
        "device": info.device,
        "package": info.package,
        "pin_mux_count": len(info.pin_mux),
        "peripheral_count": len(info.peripherals),
        "source_format": info.source_format,
    }


@router.post("/device/list-available")
async def list_importable_devices(req: DeviceImportRequest):
    """List devices available for import at a given path."""
    from core.importers.cubemx_importer import CubeMXImporter
    from core.importers.svd_parser import SVDParser
    from core.importers.cmsis_pack_importer import CMSISPackImporter
    from core.importers.atdf_importer import ATDFImporter
    from core.importers.illd_pin_extractor import ILLDPinExtractor

    importers = [CubeMXImporter(), ILLDPinExtractor(), ATDFImporter(), SVDParser(), CMSISPackImporter()]
    for imp in importers:
        if imp.can_import(req.path):
            devices = imp.list_available_devices(req.path)
            # Mark already-imported devices
            from core.device_db import get_device_db
            db = get_device_db()
            imported_names = {d["device"] for d in db.list_devices()}
            return {
                "format": imp.source_format,
                "devices": devices[:500],
                "already_imported": [d for d in devices[:500] if d in imported_names],
            }

    raise HTTPException(400, "No compatible importer found for the given path.")


class BulkImportRequest(BaseModel):
    path: str
    devices: List[str] = []  # Empty = import all


@router.post("/device/import-bulk")
async def bulk_import_devices(req: BulkImportRequest):
    """Import multiple devices from a path. If devices list is empty, imports all."""
    import asyncio
    from core.device_db import get_device_db
    from core.importers.cubemx_importer import CubeMXImporter
    from core.importers.svd_parser import SVDParser
    from core.importers.cmsis_pack_importer import CMSISPackImporter
    from core.importers.atdf_importer import ATDFImporter
    from core.importers.illd_pin_extractor import ILLDPinExtractor

    importers = [CubeMXImporter(), ILLDPinExtractor(), ATDFImporter(), SVDParser(), CMSISPackImporter()]
    importer = None
    for imp in importers:
        if imp.can_import(req.path):
            importer = imp
            break

    if not importer:
        raise HTTPException(400, "No compatible importer found.")

    device_names = req.devices if req.devices else importer.list_available_devices(req.path)
    # Cap to prevent runaway imports
    device_names = device_names[:200]

    log.step(f"Bulk importing {len(device_names)} devices…", f"Source: {req.path}")

    def _do_import():
        db = get_device_db()
        results = {"imported": 0, "failed": 0, "skipped": 0, "devices": []}
        for i, name in enumerate(device_names):
            try:
                info = importer.import_device(req.path, name)
                if info and info.pin_mux:
                    db.import_device(info)
                    results["imported"] += 1
                    results["devices"].append({"device": info.device, "pins": len(info.pin_mux)})
                elif info:
                    results["skipped"] += 1
                else:
                    results["failed"] += 1
            except Exception:
                results["failed"] += 1
            if (i + 1) % 10 == 0:
                log.info(f"Bulk import progress: {i + 1}/{len(device_names)}")
        return results

    results = await asyncio.to_thread(_do_import)

    log.success(
        f"Bulk import complete: {results['imported']} imported, {results['skipped']} skipped, {results['failed']} failed"
    )
    return results


@router.get("/device/imported")
async def list_imported_devices():
    """List all devices in the local device database."""
    from core.device_db import get_device_db
    db = get_device_db()
    return {"devices": db.list_devices(), "total": db.get_device_count()}


@router.delete("/device/{device_name}")
async def delete_imported_device(device_name: str):
    """Remove a device from the device database."""
    from core.device_db import get_device_db
    db = get_device_db()
    device_id = db.find_device(device_name)
    if device_id is None:
        raise HTTPException(404, f"Device '{device_name}' not found")
    conn = db._get_conn()
    conn.execute("DELETE FROM pin_mux WHERE device_id=?", (device_id,))
    conn.execute("DELETE FROM peripherals WHERE device_id=?", (device_id,))
    conn.execute("DELETE FROM registers WHERE device_id=?", (device_id,))
    conn.execute("DELETE FROM devices WHERE id=?", (device_id,))
    conn.commit()
    return {"status": "deleted", "device": device_name}


@router.get("/device/{device_name}/pins")
async def get_device_pins(device_name: str, peripheral_type: str = ""):
    """Get pin-mux data for an imported device."""
    from core.device_db import get_device_db
    db = get_device_db()
    device_id = db.find_device(device_name)
    if device_id is None:
        raise HTTPException(404, f"Device '{device_name}' not found in database")

    pins = db.get_pin_mux(device_id, peripheral_type)
    return {
        "device": device_name,
        "peripheral_type": peripheral_type or "all",
        "count": len(pins),
        "pins": [
            {"pin": p.pin_name, "signal": p.signal, "af": p.af_number,
             "peripheral": p.peripheral, "type": p.peripheral_type}
            for p in pins
        ],
    }


class GenerateBoardRequest(BaseModel):
    board_name: str
    led_pin: str = ""
    led_label: str = "LED"
    button_pin: str = ""
    button_label: str = "BTN"
    vcp_tx: str = ""
    vcp_rx: str = ""
    vcp_peripheral: str = ""
    plugin: str = "stm32_hal"


@router.post("/device/{device_name}/generate-board")
async def generate_board_yaml(device_name: str, req: GenerateBoardRequest):
    """Auto-generate a board YAML file from imported device data."""
    from core.device_db import get_device_db
    from core.board_registry import get_board_registry

    db = get_device_db()
    device_id = db.find_device(device_name)
    if device_id is None:
        raise HTTPException(404, f"Device '{device_name}' not found in database")

    # Get device metadata
    devices = db.list_devices()
    device_meta = next((d for d in devices if d["device"] == device_name), None)
    if not device_meta:
        raise HTTPException(404, "Device metadata not found")

    vendor = device_meta.get("vendor", "Unknown")
    family = device_meta.get("family", "")

    # Build YAML content
    lines = [
        f"name: {req.board_name}",
        f"vendor: {vendor}",
        f"family: {family}",
        f"mcu: {device_name}",
        f"clock_hz: 0",
        f"plugin: {req.plugin}",
    ]

    onboard_lines = []
    if req.led_pin:
        onboard_lines.append(f"  led: {{pin: {req.led_pin}, label: {req.led_label}, active: high}}")
    if req.button_pin:
        onboard_lines.append(f"  button: {{pin: {req.button_pin}, label: {req.button_label}, active: low}}")
    if req.vcp_tx and req.vcp_rx:
        onboard_lines.append(f"  vcp: {{tx: {req.vcp_tx}, rx: {req.vcp_rx}, peripheral: {req.vcp_peripheral or 'UART0'}, baud: 115200}}")

    if onboard_lines:
        lines.append("onboard:")
        lines.extend(onboard_lines)

    yaml_content = "\n".join(lines) + "\n"

    # Write to boards directory
    boards_dir = Path(__file__).resolve().parent.parent.parent / "boards"
    vendor_dir = boards_dir / vendor.lower().split()[0]
    vendor_dir.mkdir(parents=True, exist_ok=True)

    safe_name = req.board_name.lower().replace(" ", "-")
    safe_name = "".join(c for c in safe_name if c.isalnum() or c in "-_")
    filepath = vendor_dir / f"{safe_name}.yaml"
    filepath.write_text(yaml_content, encoding="utf-8")

    # Refresh board registry
    get_board_registry().refresh()

    log.success(f"Generated board YAML: {filepath.name}", f"Board: {req.board_name}")

    return {
        "board_name": req.board_name,
        "file": str(filepath),
        "content": yaml_content,
    }


@router.get("/discover")
async def auto_discover():
    """Auto-detect installed SDKs, toolchains, and device data sources."""
    from core.auto_discovery import discover_all
    tools = discover_all()
    return {
        "found": len(tools),
        "tools": [
            {"name": t.name, "kind": t.kind, "path": t.path,
             "vendor": t.vendor, "version": t.version, "importable": t.importable}
            for t in tools
        ],
    }


class RegisterSdkRequest(BaseModel):
    name: str
    path: str
    vendor: str = ""
    kind: str = "sdk"


@router.post("/discover/register")
async def register_sdk(req: RegisterSdkRequest):
    """Register a custom SDK path for persistent discovery."""
    from core.auto_discovery import register_sdk_path
    if not Path(req.path).exists():
        raise HTTPException(400, f"Path does not exist: {req.path}")
    register_sdk_path(req.name, req.path, req.vendor, req.kind)
    log.info(f"Registered SDK path: {req.name}", req.path)
    return {"status": "registered", "name": req.name, "path": req.path}


@router.post("/discover/unregister")
async def unregister_sdk(req: RegisterSdkRequest):
    """Remove a registered SDK path."""
    from core.auto_discovery import unregister_sdk_path
    unregister_sdk_path(req.path)
    return {"status": "unregistered", "path": req.path}


class BrowseRequest(BaseModel):
    path: str = ""


@router.post("/browse")
async def browse_directory(req: BrowseRequest):
    """Browse local filesystem for SDK/device data selection."""
    import platform as plat

    if not req.path:
        # Return common root paths
        if plat.system() == "Windows":
            import string
            drives = [f"{d}:/" for d in string.ascii_uppercase
                      if Path(f"{d}:/").exists()]
            return {"path": "", "entries": [
                {"name": d, "type": "drive", "path": d} for d in drives
            ]}
        else:
            return {"path": "/", "entries": [
                {"name": d.name, "type": "directory", "path": str(d)}
                for d in sorted(Path("/").iterdir()) if d.is_dir() and not d.name.startswith(".")
            ][:30]}

    p = Path(req.path).resolve()
    if not p.exists():
        raise HTTPException(404, f"Path not found: {req.path}")
    if not p.is_dir():
        raise HTTPException(400, "Path is not a directory")

    entries = []
    # Parent link
    if p.parent != p:
        entries.append({"name": "..", "type": "directory", "path": str(p.parent)})

    try:
        for child in sorted(p.iterdir(), key=lambda c: (not c.is_dir(), c.name.lower())):
            if child.name.startswith("."):
                continue
            entry_type = "directory" if child.is_dir() else "file"
            suffix = child.suffix.lower()
            # Only show relevant file types
            if child.is_file() and suffix not in (".xml", ".svd", ".pack", ".atdf", ".pdsc"):
                continue
            entries.append({
                "name": child.name,
                "type": entry_type,
                "path": str(child),
                "size": child.stat().st_size if child.is_file() else None,
            })
    except PermissionError:
        raise HTTPException(403, "Permission denied")

    return {"path": str(p), "entries": entries[:200]}


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

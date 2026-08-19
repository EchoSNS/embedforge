"""
Project Packager — transforms generated code into buildable vendor-specific projects.

Separates files into production/test/mock categories, adds build system files,
and packages everything into a downloadable ZIP.
"""

from __future__ import annotations

import io
import json
import logging
import zipfile
from typing import Any, Dict, List, Optional, Tuple

from plugins.base import BoardConfig, PluginRegistry

logger = logging.getLogger(__name__)


def classify_files(files: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    """Split generated files into production, test, and mock categories."""
    production, tests, mocks = {}, {}, {}
    for name, content in files.items():
        base = name.rsplit("/", 1)[-1]
        if base.startswith("mock_"):
            mocks[name] = content
        elif base.startswith("test_"):
            tests[name] = content
        else:
            production[name] = content
    return production, tests, mocks


def package_project(
    registry: PluginRegistry,
    generated_code: Dict[str, str],
    board_name: str,
    user_input: str = "",
    requirements: Optional[Dict] = None,
) -> bytes:
    """Package generated code into a downloadable ZIP with proper project structure."""
    board = registry.get_board_template(board_name)
    config = board.get_config()
    production, tests, mocks = classify_files(generated_code)

    project_files: Dict[str, str] = {}

    # Production code in src/ directory
    for name, content in production.items():
        project_files[f"src/{name}"] = content

    # Tests in tests/ directory
    for name, content in tests.items():
        project_files[f"tests/{name}"] = content

    # Mocks in tests/mocks/ directory
    for name, content in mocks.items():
        project_files[f"tests/mocks/{name}"] = content

    # Use plugin's project exporter if available
    exporter = registry.get_project_exporter()
    if exporter:
        build_files = exporter.get_project_files(config)
        project_files.update(build_files)
    else:
        # Generic CMake fallback
        project_files["CMakeLists.txt"] = _generic_cmake(config, production)

    # Add linker script if available
    linker = board.get_linker_script()
    if linker:
        project_files["linker_script.ld"] = linker

    # Add project manifest
    manifest = {
        "board": config.name,
        "mcu": config.mcu,
        "mcu_family": config.mcu_family,
        "clock_hz": config.clock_hz,
        "build_system": exporter.get_build_system() if exporter else "cmake",
        "files": {"production": list(production.keys()), "tests": list(tests.keys()), "mocks": list(mocks.keys())},
    }
    project_files["project.json"] = json.dumps(manifest, indent=2)

    # Package as ZIP
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in sorted(project_files.items()):
            zf.writestr(path, content)
    buf.seek(0)

    logger.info("Packaged project: %d files (%d prod, %d test, %d mock)",
                len(project_files), len(production), len(tests), len(mocks))
    return buf.getvalue()


def _generic_cmake(config: BoardConfig, sources: Dict[str, str]) -> str:
    """Generate a minimal CMakeLists.txt for the project."""
    src_files = [f"src/{n}" for n in sources if n.endswith(".c")]
    return f"""cmake_minimum_required(VERSION 3.20)
project({config.name.replace("-", "_")} C)

set(CMAKE_C_STANDARD 11)

# MCU: {config.mcu} @ {config.clock_hz // 1_000_000}MHz

add_executable(${{PROJECT_NAME}}
    {chr(10).join(f"    {f}" for f in src_files)}
)

target_include_directories(${{PROJECT_NAME}} PRIVATE src/Core/Inc src/)

# TODO: Add SDK include paths and toolchain file for cross-compilation
# target_include_directories(${{PROJECT_NAME}} PRIVATE ${{SDK_PATH}}/...)
# set(CMAKE_C_COMPILER arm-none-eabi-gcc)
"""

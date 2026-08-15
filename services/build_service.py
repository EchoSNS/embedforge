"""
Build Service — abstract interface for remote/local compilation and flashing.

The core workflow uses this to compile generated code without knowing
the target toolchain details (handled by the plugin's CompilerBackend).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from plugins.base import CompilationResult, PluginRegistry

logger = logging.getLogger(__name__)


@dataclass
class BuildRequest:
    """Request to build a set of source files."""

    source_files: Dict[str, str]  # filename → content
    board_name: str
    target_mcu: str = ""
    extra_flags: List[str] = None


@dataclass
class BuildResponse:
    """Response from a build attempt."""

    success: bool
    compilation_result: Optional[CompilationResult] = None
    output_binary: Optional[str] = None
    log: str = ""


class BuildService(ABC):
    """Abstract build service — implementations can be local or remote (HTTP)."""

    @abstractmethod
    def build(self, request: BuildRequest) -> BuildResponse:
        """Compile the source files for the target board."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the build service is ready."""


class LocalBuildService(BuildService):
    """
    Local build service using the plugin's CompilerBackend directly.

    Suitable for development when the toolchain is installed on the same machine.
    """

    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry

    def is_available(self) -> bool:
        compiler = self._registry.get_compiler()
        return compiler.is_available()

    def build(self, request: BuildRequest) -> BuildResponse:
        import tempfile
        from pathlib import Path

        compiler = self._registry.get_compiler()
        if not compiler.is_available():
            logger.error("Build requested but compiler is not available")
            return BuildResponse(
                success=False, log="Compiler not available. Install the toolchain."
            )

        board = self._registry.get_board_template(request.board_name)
        include_paths = board.get_sdk_include_paths()
        logger.info(
            "Starting build: board=%s, mcu=%s, files=%d, includes=%d",
            request.board_name, request.target_mcu, len(request.source_files), len(include_paths),
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_paths = []

            for name, content in request.source_files.items():
                fpath = tmp_path / name
                fpath.parent.mkdir(parents=True, exist_ok=True)
                fpath.write_text(content, encoding="utf-8")
                if name.endswith(".c"):
                    source_paths.append(str(fpath))

            output_path = str(tmp_path / "output.elf")
            all_includes = include_paths + [str(tmp_path)]

            result = compiler.compile(
                source_files=source_paths,
                include_paths=all_includes,
                output_path=output_path,
                target_mcu=request.target_mcu,
                extra_flags=request.extra_flags,
            )

            if result.success:
                logger.info("Build succeeded: %s", output_path)
            else:
                logger.warning("Build failed: %d error(s)", len(result.errors))

            return BuildResponse(
                success=result.success,
                compilation_result=result,
                output_binary=output_path if result.success else None,
                log=result.stderr,
            )

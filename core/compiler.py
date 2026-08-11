"""
Compiler Service — compile generated code via the active plugin's compiler backend.

Orchestrates compilation, error parsing, and result formatting.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from plugins.base import CompilationResult, CompilerBackend, PluginRegistry

logger = logging.getLogger(__name__)


class CompilerService:
    """
    Application-level compiler interface.

    Delegates to the plugin's CompilerBackend and adds structured
    error reporting suitable for the fix loop.
    """

    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry

    @property
    def _backend(self) -> CompilerBackend:
        return self._registry.get_compiler()

    def is_available(self) -> bool:
        return self._backend.is_available()

    def get_info(self) -> Dict[str, Any]:
        return self._backend.get_info()

    def compile(
        self,
        source_files: List[str],
        include_paths: List[str],
        output_path: str,
        target_mcu: str = "",
        extra_flags: Optional[List[str]] = None,
    ) -> CompilationResult:
        return self._backend.compile(
            source_files=source_files,
            include_paths=include_paths,
            output_path=output_path,
            target_mcu=target_mcu,
            extra_flags=extra_flags,
        )

    def format_errors_for_llm(self, result: CompilationResult) -> str:
        """Format compilation errors into an LLM-consumable text block."""
        if result.success:
            return "Compilation successful — no errors."

        lines = ["=== COMPILER ERRORS ==="]
        for i, err in enumerate(result.errors, 1):
            file_ = err.get("file", "")
            line_ = err.get("line", "")
            msg = err.get("message", str(err))
            loc = f"{file_}:{line_}" if file_ else ""
            lines.append(f"  [{i}] {loc} error: {msg}")

        if result.warnings:
            lines.append("\n=== COMPILER WARNINGS ===")
            for i, warn in enumerate(result.warnings, 1):
                msg = warn.get("message", str(warn))
                lines.append(f"  [{i}] warning: {msg}")

        return "\n".join(lines)

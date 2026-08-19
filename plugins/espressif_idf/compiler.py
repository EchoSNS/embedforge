"""ESP-IDF compiler — xtensa-esp32-elf-gcc or riscv32-esp-elf-gcc."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from plugins.base import CompilationResult, CompilerBackend

logger = logging.getLogger(__name__)


class ESPCompiler(CompilerBackend):
    """ESP-IDF toolchain detection (idf.py build is the standard build system)."""

    def __init__(self) -> None:
        self._idf_path = shutil.which("idf.py")
        self._xtensa = shutil.which("xtensa-esp32-elf-gcc")
        self._riscv = shutil.which("riscv32-esp-elf-gcc")

    def is_available(self) -> bool:
        return self._idf_path is not None or self._xtensa is not None or self._riscv is not None

    def get_info(self) -> Dict[str, Any]:
        if not self.is_available():
            return {
                "available": False,
                "message": "ESP-IDF toolchain not found. Install ESP-IDF and source export.sh.",
                "download_url": "https://docs.espressif.com/projects/esp-idf/en/latest/esp32/get-started/",
            }
        return {
            "available": True,
            "type": "esp-idf",
            "idf_path": self._idf_path or "",
            "xtensa": self._xtensa or "",
            "riscv": self._riscv or "",
        }

    def compile(self, source_files: List[str], include_paths: List[str],
                output_path: str, target_mcu: str = "",
                extra_flags: Optional[List[str]] = None) -> CompilationResult:
        # ESP-IDF uses CMake/idf.py — direct gcc invocation is non-standard
        # For validation, we can try a syntax-check-only compile
        gcc = self._xtensa or self._riscv
        if not gcc:
            return CompilationResult(success=False, stderr="ESP toolchain not available")

        cmd = [gcc, "-fsyntax-only", "-Wall"]
        for inc in include_paths:
            cmd.extend(["-I", inc])
        cmd.extend(source_files)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return CompilationResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                command=" ".join(cmd),
            )
        except (subprocess.TimeoutExpired, OSError) as e:
            return CompilationResult(success=False, stderr=str(e))

    def parse_errors(self, stderr: str) -> List[Dict[str, Any]]:
        return []

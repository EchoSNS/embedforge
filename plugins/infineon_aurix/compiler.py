"""AURIX TriCore compiler backend."""
from __future__ import annotations
import logging
import shutil
import subprocess
from typing import Any, Dict, List, Optional
from plugins.base import CompilationResult, CompilerBackend

logger = logging.getLogger(__name__)

class TriCoreCompiler(CompilerBackend):
    """TriCore GCC or TASKING compiler detection for AURIX."""

    def __init__(self) -> None:
        self._tricore_gcc = shutil.which("tricore-elf-gcc")
        self._tasking = shutil.which("ctc")  # TASKING TriCore compiler

    def is_available(self) -> bool:
        return self._tricore_gcc is not None or self._tasking is not None

    def get_info(self) -> Dict[str, Any]:
        if not self.is_available():
            return {
                "available": False,
                "message": "TriCore toolchain not found. Install AURIX Development Studio or tricore-elf-gcc.",
                "download_url": "https://www.infineon.com/cms/en/product/promopages/aurix-development-studio/",
            }
        return {
            "available": True,
            "type": "tricore",
            "tricore_gcc": self._tricore_gcc or "",
            "tasking": self._tasking or "",
        }

    def compile(self, source_files: List[str], include_paths: List[str],
                output_path: str, target_mcu: str = "",
                extra_flags: Optional[List[str]] = None) -> CompilationResult:
        gcc = self._tricore_gcc
        if not gcc:
            return CompilationResult(success=False, stderr="TriCore GCC not available")

        cmd = [gcc, "-mcpu=tc39xx", "-c", "-Wall"]
        for inc in include_paths:
            cmd.extend(["-I", inc])
        if extra_flags:
            cmd.extend(extra_flags)
        cmd.extend(source_files)
        cmd.extend(["-o", output_path])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
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

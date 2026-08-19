"""
ARM GCC Compiler Backend — arm-none-eabi-gcc for STM32 targets.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from plugins.base import CompilationResult, CompilerBackend

logger = logging.getLogger(__name__)

_MCU_FLAGS: Dict[str, List[str]] = {
    "STM32F446": ["-mcpu=cortex-m4", "-mthumb", "-mfloat-abi=hard", "-mfpu=fpv4-sp-d16"],
    "STM32F407": ["-mcpu=cortex-m4", "-mthumb", "-mfloat-abi=hard", "-mfpu=fpv4-sp-d16"],
    "STM32G474": ["-mcpu=cortex-m4", "-mthumb", "-mfloat-abi=hard", "-mfpu=fpv4-sp-d16"],
    "STM32L476": ["-mcpu=cortex-m4", "-mthumb", "-mfloat-abi=hard", "-mfpu=fpv4-sp-d16"],
}


class ARMGCCCompiler(CompilerBackend):
    """arm-none-eabi-gcc compiler backend for Cortex-M targets."""

    def __init__(self) -> None:
        self._gcc_path = shutil.which("arm-none-eabi-gcc")

    def is_available(self) -> bool:
        return self._gcc_path is not None

    def get_info(self) -> Dict[str, Any]:
        if not self.is_available():
            return {
                "available": False,
                "message": "arm-none-eabi-gcc not found in PATH. Install GNU Arm Embedded Toolchain.",
                "download_url": "https://developer.arm.com/downloads/-/gnu-rm",
            }

        try:
            result = subprocess.run(
                [self._gcc_path, "--version"],
                capture_output=True, text=True, timeout=10,
            )
            version_line = result.stdout.split("\n")[0]
        except Exception:
            version_line = "unknown"

        return {
            "available": True,
            "type": "arm-none-eabi-gcc",
            "path": self._gcc_path,
            "version": version_line,
        }

    def compile(
        self,
        source_files: List[str],
        include_paths: List[str],
        output_path: str,
        target_mcu: str = "",
        extra_flags: Optional[List[str]] = None,
    ) -> CompilationResult:
        if not self.is_available():
            return CompilationResult(
                success=False,
                stderr="arm-none-eabi-gcc not found",
                errors=({"message": "Compiler not installed"},),
            )

        cmd = [self._gcc_path]

        # MCU-specific flags
        mcu_key = target_mcu.upper().replace("X", "").rstrip("0123456789") + target_mcu[-3:]
        for key, flags in _MCU_FLAGS.items():
            if key.startswith(target_mcu.upper()[:7]):
                cmd.extend(flags)
                break
        else:
            cmd.extend(["-mcpu=cortex-m4", "-mthumb"])

        # Include paths
        for inc in include_paths:
            cmd.extend(["-I", inc])

        # Standard flags
        cmd.extend(["-Wall", "-Wextra", "-O2", "-c"])

        if extra_flags:
            cmd.extend(extra_flags)

        # Compile each source file
        cmd.extend(source_files)
        cmd.extend(["-o", output_path])

        command_str = " ".join(cmd)
        logger.info(f"Compiling: {command_str}")

        try:
            from core.build_sandbox import sandboxed_run
            r = sandboxed_run(cmd, timeout=60)

            if r["timed_out"]:
                return CompilationResult(
                    success=False,
                    stderr="Compilation timed out (60s)",
                    errors=({"message": "Compilation timed out"},),
                    command=command_str,
                )

            errors = self.parse_errors(r["stderr"]) if r["returncode"] != 0 else []
            warnings = self._parse_warnings(r["stderr"])

            return CompilationResult(
                success=r["returncode"] == 0,
                output_file=output_path if r["returncode"] == 0 else None,
                stdout=r["stdout"],
                stderr=r["stderr"],
                errors=tuple(errors),
                warnings=tuple(warnings),
                command=command_str,
            )
        except subprocess.TimeoutExpired:
            return CompilationResult(
                success=False,
                stderr="Compilation timed out (60s)",
                errors=({"message": "Compilation timed out"},),
                command=command_str,
            )
        except FileNotFoundError:
            return CompilationResult(
                success=False,
                stderr="arm-none-eabi-gcc not found",
                errors=({"message": "Compiler binary not found"},),
                command=command_str,
            )

    def parse_errors(self, stderr: str) -> List[Dict[str, Any]]:
        errors: List[Dict[str, Any]] = []
        pattern = re.compile(r"(.+?):(\d+):(\d+):\s*error:\s*(.+)")
        for match in pattern.finditer(stderr):
            errors.append({
                "file": match.group(1),
                "line": int(match.group(2)),
                "column": int(match.group(3)),
                "message": match.group(4).strip(),
            })
        return errors

    def _parse_warnings(self, stderr: str) -> List[Dict[str, Any]]:
        warnings: List[Dict[str, Any]] = []
        pattern = re.compile(r"(.+?):(\d+):(\d+):\s*warning:\s*(.+)")
        for match in pattern.finditer(stderr):
            warnings.append({
                "file": match.group(1),
                "line": int(match.group(2)),
                "column": int(match.group(3)),
                "message": match.group(4).strip(),
            })
        return warnings

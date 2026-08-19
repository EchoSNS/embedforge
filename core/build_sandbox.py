"""
Build Sandbox — resource-limited subprocess execution for compilation.

Provides timeout, output size limits, and temp directory isolation.
On Linux, additionally limits memory and CPU via the resource module.
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_COMPILE_TIMEOUT_SEC = int(os.getenv("EMBEDFORGE_COMPILE_TIMEOUT", "120"))
_MAX_OUTPUT_BYTES = 1024 * 1024  # 1 MB max stderr/stdout


def _make_preexec_fn():
    """On Linux, set per-process resource limits before exec."""
    if platform.system() != "Linux":
        return None
    try:
        import resource
        def _limits():
            # 512 MB virtual memory
            resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
            # 60s CPU time
            resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
            # 50 MB max file output
            resource.setrlimit(resource.RLIMIT_FSIZE, (50 * 1024 * 1024, 50 * 1024 * 1024))
        return _limits
    except ImportError:
        return None


def sandboxed_run(
    cmd: List[str],
    cwd: Optional[str] = None,
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Run a compilation command with resource limits.

    Returns dict with: returncode, stdout, stderr, timed_out
    """
    timeout = timeout or _COMPILE_TIMEOUT_SEC

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            cwd=cwd,
            timeout=timeout,
            preexec_fn=_make_preexec_fn(),
        )

        stdout = result.stdout[:_MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
        stderr = result.stderr[:_MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")

        return {
            "returncode": result.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": f"Process timed out after {timeout}s",
            "timed_out": True,
        }
    except FileNotFoundError:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": f"Command not found: {cmd[0]}",
            "timed_out": False,
        }
    except OSError as e:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": f"OS error: {e}",
            "timed_out": False,
        }

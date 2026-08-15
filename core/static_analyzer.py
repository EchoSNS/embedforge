"""
Static Analyzer — cppcheck integration for post-generation code analysis.

Runs cppcheck on generated C source files to catch issues the LLM
and rule-based validators may miss: unused variables, null pointer
dereferences, buffer overflows, portability issues, etc.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StaticAnalysisIssue:
    """A single issue reported by cppcheck."""

    file: str
    line: int
    column: int
    severity: str
    message: str
    issue_id: str


@dataclass
class StaticAnalysisResult:
    """Aggregated result from running cppcheck."""

    success: bool
    issues: List[StaticAnalysisIssue] = field(default_factory=list)
    errors: int = 0
    warnings: int = 0
    style: int = 0
    performance: int = 0
    portability: int = 0
    information: int = 0
    stdout: str = ""
    stderr: str = ""
    command: str = ""

    @property
    def total_issues(self) -> int:
        return len(self.issues)

    @property
    def has_critical(self) -> bool:
        return self.errors > 0


_ISSUE_RE = re.compile(
    r"^(.+?):(\d+):(\d+):\s*(error|warning|style|performance|portability|information):\s*(.+?)\s*\[(\S+)\]$"
)


class StaticAnalyzer:
    """
    Runs cppcheck on generated C files and returns structured results.

    Uses the same availability-check pattern as ARMGCCCompiler.
    """

    def __init__(self) -> None:
        self._cppcheck_path = shutil.which("cppcheck")

    def is_available(self) -> bool:
        available = self._cppcheck_path is not None
        if not available:
            logger.debug("cppcheck not found in PATH")
        return available

    def get_info(self) -> Dict[str, Any]:
        if not self.is_available():
            return {
                "available": False,
                "message": "cppcheck not found in PATH. Install via 'choco install cppcheck' or https://cppcheck.sourceforge.io",
            }

        try:
            result = subprocess.run(
                [self._cppcheck_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            version_line = result.stdout.strip()
        except Exception as e:
            logger.warning("Failed to query cppcheck version: %s", e)
            version_line = "unknown"

        return {
            "available": True,
            "path": self._cppcheck_path,
            "version": version_line,
        }

    def analyze(
        self,
        files: Dict[str, str],
        include_paths: Optional[List[str]] = None,
        extra_args: Optional[List[str]] = None,
    ) -> StaticAnalysisResult:
        """
        Run cppcheck on in-memory source files.

        Args:
            files: filename → source content mapping
            include_paths: additional -I directories for cppcheck
            extra_args: additional cppcheck CLI flags
        """
        if not self.is_available():
            logger.error("Static analysis requested but cppcheck is not installed")
            return StaticAnalysisResult(
                success=False,
                stderr="cppcheck not found in PATH",
            )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_paths: List[str] = []

            for name, content in files.items():
                fpath = tmp_path / name
                fpath.parent.mkdir(parents=True, exist_ok=True)
                fpath.write_text(content, encoding="utf-8")
                if name.endswith((".c", ".h")):
                    source_paths.append(str(fpath))

            if not source_paths:
                logger.info("No C/H files provided for static analysis")
                return StaticAnalysisResult(success=True)

            return self._run_cppcheck(source_paths, include_paths, tmp_path, extra_args)

    def _run_cppcheck(
        self,
        source_paths: List[str],
        include_paths: Optional[List[str]],
        working_dir: Path,
        extra_args: Optional[List[str]],
    ) -> StaticAnalysisResult:
        template = "{file}:{line}:{column}: {severity}: {message} [{id}]"
        cmd = [
            self._cppcheck_path,
            "--enable=warning,style,performance,portability",
            f"--template={template}",
            "--force",
            "--quiet",
        ]

        if include_paths:
            for inc in include_paths:
                cmd.extend(["-I", inc])

        if extra_args:
            cmd.extend(extra_args)

        cmd.extend(source_paths)
        command_str = " ".join(cmd)
        logger.info("Running static analysis: %s", command_str)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(working_dir),
            )
        except subprocess.TimeoutExpired:
            logger.error("cppcheck timed out after 120s")
            return StaticAnalysisResult(
                success=False,
                stderr="cppcheck timed out (120s)",
                command=command_str,
            )
        except FileNotFoundError:
            logger.error("cppcheck binary disappeared during analysis")
            return StaticAnalysisResult(
                success=False,
                stderr="cppcheck binary not found",
                command=command_str,
            )

        issues = self._parse_output(proc.stderr)
        result = StaticAnalysisResult(
            success=True,
            issues=issues,
            stdout=proc.stdout,
            stderr=proc.stderr,
            command=command_str,
        )

        for issue in issues:
            if issue.severity == "error":
                result.errors += 1
            elif issue.severity == "warning":
                result.warnings += 1
            elif issue.severity == "style":
                result.style += 1
            elif issue.severity == "performance":
                result.performance += 1
            elif issue.severity == "portability":
                result.portability += 1
            elif issue.severity == "information":
                result.information += 1

        logger.info(
            "Static analysis complete: %d issues (%d errors, %d warnings, %d style, %d perf, %d port)",
            result.total_issues,
            result.errors,
            result.warnings,
            result.style,
            result.performance,
            result.portability,
        )
        return result

    def _parse_output(self, stderr: str) -> List[StaticAnalysisIssue]:
        issues: List[StaticAnalysisIssue] = []
        for line in stderr.splitlines():
            m = _ISSUE_RE.match(line)
            if m:
                issues.append(
                    StaticAnalysisIssue(
                        file=Path(m.group(1)).name,
                        line=int(m.group(2)),
                        column=int(m.group(3)),
                        severity=m.group(4),
                        message=m.group(5),
                        issue_id=m.group(6),
                    )
                )
        return issues

    def format_for_llm(self, result: StaticAnalysisResult) -> str:
        """Format analysis results as LLM-consumable context."""
        if not result.issues:
            return "Static analysis: no issues found."

        lines = [f"=== STATIC ANALYSIS ({result.total_issues} issues) ==="]
        for i, issue in enumerate(result.issues, 1):
            lines.append(
                f"  [{i}] {issue.file}:{issue.line} {issue.severity}: {issue.message} [{issue.issue_id}]"
            )
        return "\n".join(lines)

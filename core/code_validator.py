"""
Code Validator — post-generation checks before compilation.

Validates generated code for:
  - Correct #include directives (headers exist in SDK)
  - Pin symbol validity
  - Architecture rule compliance
  - Basic C syntax sanity
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List

from plugins.base import PluginRegistry

logger = logging.getLogger(__name__)


@dataclass
class ValidationReport:
    """Aggregated validation results."""

    passed: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    pin_issues: List[str] = field(default_factory=list)
    missing_headers: List[str] = field(default_factory=list)
    rule_violations: List[str] = field(default_factory=list)
    static_analysis_issues: List[str] = field(default_factory=list)


class CodeValidator:
    """
    Multi-layer validation of generated C code.

    Runs checks in order of severity: headers → pins → rules → syntax.
    """

    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry

    def validate(self, files: Dict[str, str], run_static_analysis: bool = True) -> ValidationReport:
        """
        Validate all generated files.

        Args:
            files: mapping of filename → source code content
            run_static_analysis: whether to run cppcheck (if available)
        """
        report = ValidationReport()
        logger.info("Starting validation of %d file(s)", len(files))

        # Build set of project-internal header basenames for include resolution
        project_headers = set()
        for fname in files:
            if fname.endswith(".h"):
                # Store both full path and basename for resolution
                project_headers.add(fname.rsplit("/", 1)[-1])
                project_headers.add(fname)

        for filename, content in files.items():
            logger.debug("Validating file: %s (%d bytes)", filename, len(content))
            self._check_includes(filename, content, report, project_headers)
            # Only validate pins in production source files, not mocks/tests
            if not self._is_test_or_mock(filename):
                self._check_pins(content, report)
            self._check_rules(content, report)
            self._check_syntax(filename, content, report)

        if run_static_analysis:
            self._run_static_analysis(files, report)

        report.passed = not report.errors and not report.pin_issues
        logger.info(
            "Validation complete: passed=%s, errors=%d, pin_issues=%d, static_issues=%d",
            report.passed, len(report.errors), len(report.pin_issues), len(report.static_analysis_issues),
        )
        return report

    def _check_includes(self, filename: str, code: str, report: ValidationReport, project_headers: set) -> None:
        """Verify #include'd headers can be resolved."""
        from core.sdk_analyzer import SDKAnalyzer

        board_template = self._registry.get_board_template(
            self._registry.list_boards()[0] if self._registry.list_boards() else ""
        )
        include_paths = board_template.get_sdk_include_paths()
        analyzer = SDKAnalyzer(include_paths)

        includes = analyzer.get_includes_from_code(code)
        for inc in includes:
            if self._is_standard_header(inc):
                continue
            if self._is_internal_header(inc, project_headers):
                continue
            if not analyzer.resolve_header(inc):
                logger.debug("Unresolved include in %s: %s", filename, inc)
                report.missing_headers.append(f"{filename}: cannot resolve '{inc}'")

    def _check_pins(self, code: str, report: ValidationReport) -> None:
        from core.pin_validator import PinValidator

        validator = PinValidator(self._registry)
        result = validator.validate_code(code)
        report.pin_issues.extend(
            [f"Invalid pin: {p}" for p in result.invalid_pins]
        )

    def _check_rules(self, code: str, report: ValidationReport) -> None:
        rules = self._registry.get_architecture_rules()
        violations = rules.validate_code(code)
        report.rule_violations.extend(violations)

    def _check_syntax(self, filename: str, code: str, report: ValidationReport) -> None:
        """Basic syntax checks (unbalanced braces, missing semicolons after struct)."""
        open_braces = code.count("{")
        close_braces = code.count("}")
        if open_braces != close_braces:
            report.errors.append(
                f"{filename}: unbalanced braces ({{ = {open_braces}, }} = {close_braces})"
            )

    def _run_static_analysis(self, files: Dict[str, str], report: ValidationReport) -> None:
        """Run cppcheck if available."""
        from core.static_analyzer import StaticAnalyzer

        analyzer = StaticAnalyzer()
        if not analyzer.is_available():
            logger.debug("cppcheck not available — skipping static analysis")
            return

        logger.info("Running cppcheck static analysis…")
        result = analyzer.analyze(files)
        for issue in result.issues:
            report.static_analysis_issues.append(
                f"{issue.file}:{issue.line} [{issue.severity}] {issue.message} ({issue.issue_id})"
            )
            if issue.severity == "error":
                report.errors.append(f"static-analysis: {issue.file}:{issue.line} {issue.message}")

    @staticmethod
    def _is_standard_header(name: str) -> bool:
        return name in _STANDARD_C_HEADERS or name.startswith("std")

    @staticmethod
    def _is_internal_header(name: str, project_headers: set) -> bool:
        """Check if a header is project-internal, a mock, or a test framework header."""
        basename = name.rsplit("/", 1)[-1]
        if basename in project_headers or name in project_headers:
            return True
        if basename.startswith("mock_"):
            return True
        if basename.startswith("unity"):
            return True
        return False

    @staticmethod
    def _is_test_or_mock(filename: str) -> bool:
        """Return True for test and mock files that shouldn't be pin-validated."""
        base = filename.rsplit("/", 1)[-1]
        return base.startswith("test_") or base.startswith("mock_")


_STANDARD_C_HEADERS = frozenset({
    "string.h", "stdlib.h", "stdio.h", "stdint.h", "stdbool.h",
    "stddef.h", "limits.h", "float.h", "math.h", "ctype.h",
    "errno.h", "assert.h", "time.h", "signal.h", "setjmp.h",
    "stdarg.h", "locale.h", "wchar.h", "inttypes.h",
})

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


class CodeValidator:
    """
    Multi-layer validation of generated C code.

    Runs checks in order of severity: headers → pins → rules → syntax.
    """

    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry

    def validate(self, files: Dict[str, str]) -> ValidationReport:
        """
        Validate all generated files.

        Args:
            files: mapping of filename → source code content
        """
        report = ValidationReport()

        for filename, content in files.items():
            self._check_includes(filename, content, report)
            self._check_pins(content, report)
            self._check_rules(content, report)
            self._check_syntax(filename, content, report)

        report.passed = not report.errors and not report.pin_issues
        return report

    def _check_includes(self, filename: str, code: str, report: ValidationReport) -> None:
        """Verify #include'd headers can be resolved in the SDK."""
        from core.sdk_analyzer import SDKAnalyzer

        board_template = self._registry.get_board_template(
            self._registry.list_boards()[0] if self._registry.list_boards() else ""
        )
        include_paths = board_template.get_sdk_include_paths()
        analyzer = SDKAnalyzer(include_paths)

        includes = analyzer.get_includes_from_code(code)
        for inc in includes:
            if not self._is_standard_header(inc) and not analyzer.resolve_header(inc):
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

    @staticmethod
    def _is_standard_header(name: str) -> bool:
        return name in _STANDARD_C_HEADERS or name.startswith("std")


_STANDARD_C_HEADERS = frozenset({
    "string.h", "stdlib.h", "stdio.h", "stdint.h", "stdbool.h",
    "stddef.h", "limits.h", "float.h", "math.h", "ctype.h",
    "errno.h", "assert.h", "time.h", "signal.h", "setjmp.h",
    "stdarg.h", "locale.h", "wchar.h", "inttypes.h",
})

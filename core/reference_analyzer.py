"""
Reference Project Analyzer — extracts patterns from user-provided C projects.

Parses uploaded .c/.h files to understand coding patterns, peripheral usage,
and driver initialization flows. Output feeds the refiner and codegen stages.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

_RE_INCLUDE = re.compile(r'#include\s*[<"]([^>"]+)[>"]')
_RE_FUNC_DEF = re.compile(
    r"^([\w\s\*]+?)\s+(\w+)\s*\(([^)]*)\)\s*\{", re.MULTILINE
)
_RE_FUNC_CALL = re.compile(r"\b(\w+)\s*\(")
_RE_GLOBAL_VAR = re.compile(
    r"^(?:static\s+)?(?:volatile\s+)?([\w\s\*]+?)\s+(\w+)\s*(?:=|;)", re.MULTILINE
)


@dataclass
class FunctionDefinition:
    name: str
    return_type: str
    parameters: str
    file: str
    line_count: int = 0


@dataclass
class ReferenceAnalysis:
    """Structured output from analyzing a reference project."""

    files_analyzed: int = 0
    includes: List[str] = field(default_factory=list)
    functions_defined: List[FunctionDefinition] = field(default_factory=list)
    functions_called: List[str] = field(default_factory=list)
    global_variables: List[Dict[str, str]] = field(default_factory=list)
    peripherals_used: List[str] = field(default_factory=list)
    patterns: Dict[str, Any] = field(default_factory=dict)


class ReferenceProjectAnalyzer:
    """
    Analyzes user-uploaded reference C projects to extract reusable patterns.

    Vendor-agnostic: works with any C code. The plugin's driver catalog
    is used separately to map discovered function calls to known drivers.
    """

    def analyze(self, project_path: str) -> ReferenceAnalysis:
        """Analyze all .c and .h files in a project directory."""
        result = ReferenceAnalysis()
        path = Path(project_path)

        if not path.exists():
            logger.warning(f"Reference project path not found: {project_path}")
            return result

        source_files = list(path.rglob("*.c")) + list(path.rglob("*.h"))
        result.files_analyzed = len(source_files)

        all_includes: Set[str] = set()
        all_calls: Set[str] = set()

        for file in source_files:
            self._analyze_file(file, result, all_includes, all_calls)

        result.includes = sorted(all_includes)
        result.functions_called = sorted(all_calls)

        # Detect patterns
        result.patterns = self._detect_patterns(result)

        logger.info(
            f"Reference analysis: {result.files_analyzed} files, "
            f"{len(result.functions_defined)} functions, "
            f"{len(result.functions_called)} unique calls"
        )
        return result

    def analyze_files(self, files: Dict[str, str]) -> ReferenceAnalysis:
        """Analyze in-memory file contents (filename → source code)."""
        result = ReferenceAnalysis()
        result.files_analyzed = len(files)

        all_includes: Set[str] = set()
        all_calls: Set[str] = set()

        for filename, content in files.items():
            self._analyze_content(filename, content, result, all_includes, all_calls)

        result.includes = sorted(all_includes)
        result.functions_called = sorted(all_calls)
        result.patterns = self._detect_patterns(result)
        return result

    def _analyze_file(
        self,
        file: Path,
        result: ReferenceAnalysis,
        includes: Set[str],
        calls: Set[str],
    ) -> None:
        try:
            content = file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return
        self._analyze_content(file.name, content, result, includes, calls)

    def _analyze_content(
        self,
        filename: str,
        content: str,
        result: ReferenceAnalysis,
        includes: Set[str],
        calls: Set[str],
    ) -> None:
        # Includes
        for match in _RE_INCLUDE.finditer(content):
            includes.add(match.group(1))

        # Function definitions
        for match in _RE_FUNC_DEF.finditer(content):
            result.functions_defined.append(
                FunctionDefinition(
                    name=match.group(2),
                    return_type=match.group(1).strip(),
                    parameters=match.group(3).strip(),
                    file=filename,
                )
            )

        # Function calls
        for match in _RE_FUNC_CALL.finditer(content):
            name = match.group(1)
            # Filter out C keywords and common macros
            if name not in _C_KEYWORDS and not name.startswith("__"):
                calls.add(name)

        # Global variables
        for match in _RE_GLOBAL_VAR.finditer(content):
            result.global_variables.append(
                {"type": match.group(1).strip(), "name": match.group(2), "file": filename}
            )

    def _detect_patterns(self, result: ReferenceAnalysis) -> Dict[str, Any]:
        """Infer high-level patterns from the analysis."""
        patterns: Dict[str, Any] = {}

        # Detect init/deinit patterns
        init_funcs = [f for f in result.functions_defined if "init" in f.name.lower()]
        if init_funcs:
            patterns["has_init_pattern"] = True
            patterns["init_functions"] = [f.name for f in init_funcs]

        # Detect ISR patterns
        isr_funcs = [
            f
            for f in result.functions_defined
            if any(k in f.name.lower() for k in ("isr", "irq", "handler", "interrupt"))
        ]
        if isr_funcs:
            patterns["has_isr_pattern"] = True
            patterns["isr_functions"] = [f.name for f in isr_funcs]

        # Detect state machine patterns
        if any("state" in f.name.lower() for f in result.functions_defined):
            patterns["has_state_machine"] = True

        return patterns

    def format_for_llm(self, analysis: ReferenceAnalysis) -> str:
        """Format analysis for LLM context injection."""
        lines = [
            f"Reference Project Analysis ({analysis.files_analyzed} files):",
            f"  Includes: {', '.join(analysis.includes[:20])}",
            f"  Functions defined: {len(analysis.functions_defined)}",
        ]

        if analysis.functions_defined:
            lines.append("  Key functions:")
            for fn in analysis.functions_defined[:15]:
                lines.append(f"    {fn.return_type} {fn.name}({fn.parameters})")

        if analysis.patterns:
            lines.append(f"  Detected patterns: {', '.join(analysis.patterns.keys())}")

        return "\n".join(lines)


_C_KEYWORDS = frozenset({
    "if", "else", "for", "while", "do", "switch", "case", "break",
    "continue", "return", "goto", "sizeof", "typedef", "struct",
    "union", "enum", "static", "extern", "volatile", "const",
    "register", "inline", "void", "int", "char", "float", "double",
    "long", "short", "unsigned", "signed", "NULL", "TRUE", "FALSE",
})

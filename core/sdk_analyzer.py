"""
SDK Analyzer — dynamically parses SDK headers to extract API metadata.

Works with ANY C SDK by scanning header files for function declarations,
struct/enum typedefs, and macro definitions. The plugin provides
SDK-specific path resolution; this module handles the generic parsing.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

_RE_FUNC_DECL = re.compile(
    r"^[\w\s\*]+\s+(\w+)\s*\(([^)]*)\)\s*;", re.MULTILINE
)
_RE_TYPEDEF_STRUCT = re.compile(
    r"typedef\s+(?:struct|union)\s*(?:\w+\s*)?\{([^}]*)\}\s*(\w+)\s*;", re.DOTALL
)
_RE_TYPEDEF_ENUM = re.compile(
    r"typedef\s+enum\s*(?:\w+\s*)?\{([^}]*)\}\s*(\w+)\s*;", re.DOTALL
)
_RE_DEFINE = re.compile(r"^#define\s+(\w+)\s+(.+)$", re.MULTILINE)
_RE_INCLUDE = re.compile(r'#include\s*[<"]([^>"]+)[>"]')


@dataclass
class FunctionSignature:
    name: str
    return_type: str
    parameters: str
    header_file: str


@dataclass
class TypeDefinition:
    name: str
    kind: str  # "struct", "union", "enum"
    body: str
    header_file: str


@dataclass
class SDKAnalysisResult:
    """Aggregated result of analyzing an SDK directory."""

    functions: List[FunctionSignature] = field(default_factory=list)
    types: List[TypeDefinition] = field(default_factory=list)
    macros: Dict[str, str] = field(default_factory=dict)
    headers_scanned: int = 0


class SDKAnalyzer:
    """
    Scans SDK header files and extracts structured API metadata.

    Not vendor-specific — works with any C header tree.
    """

    def __init__(self, include_paths: Optional[List[str]] = None) -> None:
        self._include_paths = include_paths or []

    def analyze(self, paths: Optional[List[str]] = None) -> SDKAnalysisResult:
        """
        Scan all .h files under the given paths (or configured include paths).

        Returns structured metadata suitable for LLM context and catalog building.
        """
        scan_paths = paths or self._include_paths
        result = SDKAnalysisResult()

        for base in scan_paths:
            base_path = Path(base)
            if not base_path.exists():
                logger.warning(f"SDK path not found: {base}")
                continue

            for header in base_path.rglob("*.h"):
                self._parse_header(header, result)

        logger.info(
            f"SDK analysis complete: {result.headers_scanned} headers, "
            f"{len(result.functions)} functions, {len(result.types)} types"
        )
        return result

    def analyze_single_header(self, header_path: str) -> SDKAnalysisResult:
        result = SDKAnalysisResult()
        self._parse_header(Path(header_path), result)
        return result

    def get_includes_from_code(self, code: str) -> Set[str]:
        """Extract #include references from generated source code."""
        return set(_RE_INCLUDE.findall(code))

    def resolve_header(self, include_name: str) -> Optional[Path]:
        """Resolve a header name against configured include paths."""
        for base in self._include_paths:
            candidate = Path(base) / include_name
            if candidate.exists():
                return candidate
        return None

    def _parse_header(self, header: Path, result: SDKAnalysisResult) -> None:
        try:
            content = header.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return

        result.headers_scanned += 1
        header_name = str(header)

        # Functions
        for match in _RE_FUNC_DECL.finditer(content):
            full_match = match.group(0).strip()
            name = match.group(1)
            params = match.group(2).strip()
            ret_type = full_match[: full_match.index(name)].strip()
            result.functions.append(
                FunctionSignature(
                    name=name,
                    return_type=ret_type,
                    parameters=params,
                    header_file=header_name,
                )
            )

        # Structs/Unions
        for match in _RE_TYPEDEF_STRUCT.finditer(content):
            result.types.append(
                TypeDefinition(
                    name=match.group(2),
                    kind="struct",
                    body=match.group(1).strip(),
                    header_file=header_name,
                )
            )

        # Enums
        for match in _RE_TYPEDEF_ENUM.finditer(content):
            result.types.append(
                TypeDefinition(
                    name=match.group(2),
                    kind="enum",
                    body=match.group(1).strip(),
                    header_file=header_name,
                )
            )

        # Macros
        for match in _RE_DEFINE.finditer(content):
            result.macros[match.group(1)] = match.group(2).strip()

    def format_for_llm(self, result: SDKAnalysisResult, max_functions: int = 50) -> str:
        """Format analysis result as LLM context text."""
        lines = [f"SDK Analysis: {result.headers_scanned} headers scanned"]

        if result.functions:
            lines.append(f"\nFunctions ({len(result.functions)} total):")
            for fn in result.functions[:max_functions]:
                lines.append(f"  {fn.return_type} {fn.name}({fn.parameters});")
            if len(result.functions) > max_functions:
                lines.append(f"  ... and {len(result.functions) - max_functions} more")

        if result.types:
            lines.append(f"\nTypes ({len(result.types)} total):")
            for t in result.types[:30]:
                lines.append(f"  {t.kind} {t.name}")

        return "\n".join(lines)

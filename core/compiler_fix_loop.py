"""
Compiler Fix Loop — LLM-based iterative code repair from build errors.

Flow:
  1. Parse structured errors from a failed compilation
  2. Gather SDK context for the failing APIs
  3. Send errors + code + SDK context to LLM for repair
  4. Re-compile the fixed code
  5. Repeat until success or max iterations reached
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from config.llm_config import get_llm
from core.compiler import CompilerService
from core.sdk_analyzer import SDKAnalyzer
from plugins.base import CompilationResult, PluginRegistry

logger = logging.getLogger(__name__)


FIX_SYSTEM_PROMPT = """You are an expert embedded C developer. You are given:
1. Generated C source files that failed to compile
2. The compiler errors
3. The SDK API reference (correct function signatures and types)

Your job: fix ALL compiler errors by correcting the source code.

Rules:
- Only modify what is necessary to fix the errors
- Use the SDK reference to get correct function signatures and type names
- Do not change the overall logic or architecture
- Return the complete corrected file contents

Output format — for EACH file that needs fixing:
```filename.c
<complete corrected file content>
```
"""


class CompilerFixLoop:
    """
    Iteratively repairs generated code using LLM + compiler feedback.

    Implements a bounded retry loop with decreasing temperature to converge.
    """

    def __init__(
        self,
        registry: PluginRegistry,
        max_iterations: int = 5,
    ) -> None:
        self._registry = registry
        self._compiler = CompilerService(registry)
        self._max_iterations = max_iterations

    def run(
        self,
        source_files: Dict[str, str],
        include_paths: List[str],
        output_path: str,
        target_mcu: str = "",
    ) -> Dict[str, Any]:
        """
        Attempt to compile files, fixing errors iteratively with LLM assistance.

        Args:
            source_files: filename → source code content
            include_paths: SDK include directories
            output_path: compilation output directory
            target_mcu: target MCU identifier

        Returns:
            Dict with keys: success, files, iterations, final_result
        """
        current_files = dict(source_files)

        for iteration in range(1, self._max_iterations + 1):
            logger.info(f"Fix loop iteration {iteration}/{self._max_iterations}")

            result = self._compile(current_files, include_paths, output_path, target_mcu)

            if result.success:
                logger.info(f"Compilation succeeded on iteration {iteration}")
                return {
                    "success": True,
                    "files": current_files,
                    "iterations": iteration,
                    "final_result": result,
                }

            # Attempt LLM fix
            fixed = self._llm_fix(current_files, result, include_paths, iteration)
            if fixed:
                current_files.update(fixed)
            else:
                logger.warning(f"LLM fix returned no changes on iteration {iteration}")

        logger.info("Fix loop exhausted after %d iterations — compilation still failing", self._max_iterations)
        return {
            "success": False,
            "files": current_files,
            "iterations": self._max_iterations,
            "final_result": result,
        }

    def _compile(
        self,
        files: Dict[str, str],
        include_paths: List[str],
        output_path: str,
        target_mcu: str,
    ) -> CompilationResult:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            file_paths = []
            for name, content in files.items():
                if name.endswith(".c"):
                    fpath = Path(tmp) / name
                    fpath.write_text(content, encoding="utf-8")
                    file_paths.append(str(fpath))

            # Write headers too
            for name, content in files.items():
                if name.endswith(".h"):
                    fpath = Path(tmp) / name
                    fpath.write_text(content, encoding="utf-8")

            all_includes = include_paths + [tmp]

            return self._compiler.compile(
                source_files=file_paths,
                include_paths=all_includes,
                output_path=output_path,
                target_mcu=target_mcu,
            )

    def _llm_fix(
        self,
        files: Dict[str, str],
        result: CompilationResult,
        include_paths: List[str],
        iteration: int,
    ) -> Optional[Dict[str, str]]:
        """Use LLM to fix compilation errors."""
        logger.info("LLM fix attempt %d: %d error(s) to resolve", iteration, len(result.errors))
        error_text = self._compiler.format_errors_for_llm(result)
        sdk_context = self._gather_sdk_context(files, include_paths)

        file_block = "\n".join(
            f"```{name}\n{content}\n```" for name, content in files.items()
        )

        user_prompt = (
            f"Fix the following compilation errors.\n\n"
            f"ERRORS:\n{error_text}\n\n"
            f"SOURCE FILES:\n{file_block}\n\n"
            f"SDK REFERENCE:\n{sdk_context}\n\n"
            f"Return the corrected files."
        )

        # Decrease temperature on later iterations for more conservative fixes
        temp = max(0.0, 0.3 - (iteration * 0.05))
        llm = get_llm()

        try:
            response = llm.invoke([
                SystemMessage(content=FIX_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ])
            fixed = self._parse_fix_response(response.content)
            logger.info("LLM fix returned %d corrected file(s)", len(fixed))
            return fixed
        except Exception as e:
            logger.error("LLM fix failed on iteration %d: %s", iteration, e)
            return None

    def _gather_sdk_context(self, files: Dict[str, str], include_paths: List[str]) -> str:
        """Extract relevant SDK signatures for the headers referenced by the failing code."""
        analyzer = SDKAnalyzer(include_paths)
        all_includes: set = set()

        for content in files.values():
            all_includes.update(analyzer.get_includes_from_code(content))

        context_parts: List[str] = []
        for inc in sorted(all_includes):
            resolved = analyzer.resolve_header(inc)
            if resolved:
                result = analyzer.analyze_single_header(str(resolved))
                if result.functions:
                    context_parts.append(f"// From {inc}:")
                    for fn in result.functions[:10]:
                        context_parts.append(f"  {fn.return_type} {fn.name}({fn.parameters});")

        return "\n".join(context_parts) if context_parts else "No SDK context available."

    def _parse_fix_response(self, response: str) -> Dict[str, str]:
        """Extract file contents from LLM response formatted as ```filename ... ```."""
        files: Dict[str, str] = {}
        pattern = re.compile(r"```(\S+\.(?:c|h))\n(.*?)```", re.DOTALL)

        for match in pattern.finditer(response):
            filename = match.group(1)
            content = match.group(2).strip()
            files[filename] = content

        return files

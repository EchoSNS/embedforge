"""
TDD Generator — orchestrates Red-Green-Refactor code generation.

Generates mock infrastructure, Unity tests, and production code
in a structured pipeline:
  1. Mock Generation — stub the SDK APIs
  2. Test Generation — write failing tests (Red)
  3. Production Code — implement to pass tests (Green)
  4. Validation — compile mocks+tests with Unity to verify
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from config.llm_config import get_llm
from plugins.base import PluginRegistry

logger = logging.getLogger(__name__)

# Type alias for progress callbacks: (phase_name, detail_message)
ProgressCallback = Callable[[str, str], None]


class TDDPhase(Enum):
    MOCK_GENERATION = "mock_generation"
    TEST_GENERATION = "test_generation"
    PRODUCTION_CODE = "production_code"
    VALIDATION = "validation"


@dataclass
class TDDResult:
    """Outcome of a TDD generation run."""

    success: bool
    phase: TDDPhase
    mock_files: Dict[str, str] = field(default_factory=dict)
    test_files: Dict[str, str] = field(default_factory=dict)
    production_files: Dict[str, str] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    error_detail: str = ""


class TDDGenerator:
    """
    Orchestrates TDD-based embedded C code generation.

    Each phase uses a specialized LLM prompt. The generator
    is vendor-agnostic — plugin provides driver context.
    """

    def __init__(self, registry: PluginRegistry, session_id: str = "") -> None:
        self._registry = registry
        self._session_id = session_id

    def generate(
        self,
        requirements: Dict[str, Any],
        driver_context: str,
        pin_context: str,
        architecture_rules: str,
        reference_context: str = "",
        on_progress: Optional[ProgressCallback] = None,
    ) -> TDDResult:
        """
        Run the full TDD generation pipeline.

        Args:
            requirements: structured requirements from the workflow state
            driver_context: SDK driver API info for LLM
            pin_context: validated pin symbols for LLM
            architecture_rules: SDK coding rules for LLM
            reference_context: optional reference project patterns
            on_progress: optional callback for phase progress updates
        """
        def _progress(phase: str, detail: str = "") -> None:
            if on_progress:
                on_progress(phase, detail)

        # Phase 1: Mock generation
        _progress("mock_generation", "Building mock/stub prompt for SDK driver APIs…")
        logger.info("TDD Phase 1: Generating mocks")
        mock_result, mock_err = self._invoke_and_parse(
            self._build_mock_prompt(architecture_rules),
            (
                f"Generate mock/stub files for the following SDK drivers.\n\n"
                f"REQUIREMENTS:\n{_format_requirements(requirements)}\n\n"
                f"SDK DRIVER API:\n{driver_context}\n\n"
                f"Generate mock headers and source files that stub all SDK functions "
                f"with spy counters for unit testing."
            ),
            on_progress=on_progress,
            phase_name="mock_generation",
        )
        if not mock_result:
            logger.error("TDD Phase 1 failed: %s", mock_err)
            return TDDResult(
                success=False,
                phase=TDDPhase.MOCK_GENERATION,
                errors=[f"Mock generation failed: {mock_err}"],
                error_detail=mock_err,
            )
        _progress("mock_generation", f"Mock generation complete — {len(mock_result)} file(s): {', '.join(mock_result.keys())}")

        # Phase 2: Test generation
        _progress("test_generation", f"Building Unity test prompt with {len(mock_result)} mock file(s)…")
        logger.info("TDD Phase 2: Generating tests (mocks: %d files)", len(mock_result))
        mock_api_summary = "\n\n".join(
            f"// --- {name} ---\n{content}" for name, content in mock_result.items()
            if name.endswith(".h")
        )
        if not mock_api_summary:
            mock_api_summary = "\n".join(f"// {name}" for name in mock_result.keys())
        test_result, test_err = self._invoke_and_parse(
            self._build_test_prompt(architecture_rules),
            (
                f"Generate Unity test files for the following requirements.\n\n"
                f"REQUIREMENTS:\n{_format_requirements(requirements)}\n\n"
                f"MOCK API (use these spy variables and functions in tests):\n{mock_api_summary}\n\n"
                f"SDK API:\n{driver_context}\n\n"
                f"Write test cases that verify the production code behavior "
                f"by checking the spy counters and captured parameters from the mock. "
                f"Tests should fail initially (Red phase)."
            ),
            on_progress=on_progress,
            phase_name="test_generation",
        )
        if not test_result:
            logger.error("TDD Phase 2 failed: %s", test_err)
            return TDDResult(
                success=False,
                phase=TDDPhase.TEST_GENERATION,
                mock_files=mock_result,
                errors=[f"Test generation failed: {test_err}"],
                error_detail=test_err,
            )
        _progress("test_generation", f"Test generation complete — {len(test_result)} file(s): {', '.join(test_result.keys())}")

        # Phase 3: Production code
        _progress("production_code", f"Building production code prompt with {len(test_result)} test file(s)…")
        logger.info("TDD Phase 3: Generating production code (tests: %d files)", len(test_result))
        test_content = "\n\n".join(f"// {name}\n{content}" for name, content in test_result.items())
        prod_user_prompt = (
            f"Generate production code that passes these tests.\n\n"
            f"REQUIREMENTS:\n{_format_requirements(requirements)}\n\n"
            f"TESTS TO PASS:\n{test_content}\n\n"
            f"SDK API:\n{driver_context}\n\n"
            f"PIN ASSIGNMENTS:\n{pin_context}\n\n"
            f"ARCHITECTURE RULES:\n{architecture_rules}\n\n"
        )
        if reference_context:
            prod_user_prompt += f"REFERENCE PATTERNS:\n{reference_context}\n\n"
        prod_user_prompt += "Generate the production .c and .h files."

        prod_result, prod_err = self._invoke_and_parse(
            self._build_production_prompt(architecture_rules), prod_user_prompt,
            on_progress=on_progress,
            phase_name="production_code",
        )
        if not prod_result:
            logger.error("TDD Phase 3 failed: %s", prod_err)
            return TDDResult(
                success=False,
                phase=TDDPhase.PRODUCTION_CODE,
                mock_files=mock_result,
                test_files=test_result,
                errors=[f"Production code generation failed: {prod_err}"],
                error_detail=prod_err,
            )
        _progress("production_code", f"Production code complete — {len(prod_result)} file(s): {', '.join(prod_result.keys())}")

        logger.info(
            "TDD pipeline complete: mocks=%d, tests=%d, production=%d files",
            len(mock_result), len(test_result), len(prod_result),
        )
        return TDDResult(
            success=True,
            phase=TDDPhase.VALIDATION,
            mock_files=mock_result,
            test_files=test_result,
            production_files=prod_result,
        )

    def _invoke_and_parse(
        self,
        system_prompt: str,
        user_prompt: str,
        on_progress: Optional[ProgressCallback] = None,
        phase_name: str = "",
    ) -> tuple[Optional[Dict[str, str]], str]:
        """Invoke LLM and parse code blocks. Returns (files, error_detail)."""
        llm = get_llm(session_id=self._session_id, stage=f"codegen_{phase_name}" if phase_name else "codegen")
        try:
            if on_progress and phase_name:
                on_progress(phase_name, "Sending prompt to LLM…")
            t0 = time.time()
            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ])
            elapsed = time.time() - t0
            content = response.content
            if on_progress and phase_name:
                on_progress(phase_name, f"LLM responded in {elapsed:.1f}s ({len(content)} chars). Parsing code blocks…")

            parsed = _parse_code_blocks(content)
            if parsed is None:
                preview = content[:300].replace("\n", " ")
                detail = (
                    f"LLM responded but no code blocks (```filename.c ... ```) were found in output. "
                    f"Response preview: {preview}"
                )
                logger.warning("Code block parse failed: %s", detail)
                if on_progress and phase_name:
                    on_progress(phase_name, f"Parse failed — no code blocks found in {len(content)}-char response")
                return None, detail
            if on_progress and phase_name:
                on_progress(phase_name, f"Parsed {len(parsed)} file(s) from response")
            return parsed, ""
        except Exception as e:
            detail = f"{type(e).__name__}: {e}"
            logger.error("LLM invocation failed: %s", detail)
            if on_progress and phase_name:
                on_progress(phase_name, f"LLM call failed: {detail[:150]}")
            return None, detail

    def _build_mock_prompt(self, rules: str) -> str:
        return (
            "You are an expert embedded C test engineer.\n"
            "Generate mock/stub files for SDK drivers using a simple spy pattern.\n\n"
            "IMPORTANT naming: the mock header MUST be named `mock_<original>.h` "
            "and source `mock_<original>.c` (e.g., if the SDK header is `vendor_hal.h`, "
            "generate `mock_vendor_hal.h` and `mock_vendor_hal.c`).\n\n"
            "Each mock must:\n"
            "- Include ALL struct/enum/typedef from the real SDK header\n"
            "- Include ALL register bit-field defines and constants used by production code\n"
            "- Provide `extern uint32_t g_<func>_calls;` spy counter for each function\n"
            "- Provide `extern <ParamType> g_last_<func>_<param>;` for parameter capture\n"
            "- Provide configurable return values via extern variables for functions that return status\n"
            "- Provide `void Mock_ResetAll(void);` to clear all spies between tests\n"
            "- Do NOT use CMock, FFF, or any third-party mock framework\n"
            "- Tests will verify behavior by checking spy counters and captured params directly\n\n"
            f"SDK CONVENTIONS:\n{rules}\n\n"
            "Output format: ```filename.h\\n<content>\\n``` for each file."
        )

    def _build_test_prompt(self, rules: str) -> str:
        return (
            "You are an expert embedded C test engineer using Unity test framework.\n"
            "Generate unit test files that verify driver behavior using HAND-WRITTEN spy mocks.\n\n"
            "CRITICAL — test files MUST:\n"
            "- `#include` the mock header (`mock_<sdk_header>.h`), NOT the real SDK header\n"
            "- Use Unity `TEST_GROUP`, `TEST`, `TEST_SETUP`, `TEST_TEAR_DOWN` macros\n"
            "- In TEST_SETUP: call `Mock_ResetAll()` to reset spy counters\n"
            "- Arrange: set configurable return variables for SDK functions that return status\n"
            "- Act: call the production function under test\n"
            "- Assert: check `g_<func>_calls` for call count, `g_last_<func>_<param>` for parameters\n"
            "- Do NOT use CMock APIs (no _ExpectAndReturn, _AddCallback, _Verify, _Destroy)\n"
            "- Do NOT call mock_*_Init(), mock_*_Verify(), or mock_*_Destroy()\n"
            "- Each test verifies ONE behavior\n"
            "- Test names describe the expected behavior\n\n"
            f"SDK CONVENTIONS:\n{rules}\n\n"
            "Output format: ```test_filename.c\\n<content>\\n``` for each file."
        )

    def _build_production_prompt(self, rules: str) -> str:
        return (
            "You are an expert embedded C developer.\n"
            "Generate production code that makes the given tests pass.\n\n"
            "Rules:\n"
            "- Follow the SDK architecture rules exactly\n"
            "- Use only validated pin symbols\n"
            "- Implement all functions declared in the header\n"
            "- Follow init/deinit patterns from the SDK\n"
            "- Production headers should include the real SDK header for normal builds; "
            "tests will substitute the mock header at compile time via include path ordering\n"
            "- All register bit defines used in production code MUST exist in the mock header\n\n"
            f"SDK CONVENTIONS:\n{rules}\n\n"
            "Output format: ```filename.c\\n<content>\\n``` for each file."
        )


def _format_requirements(requirements: Dict[str, Any]) -> str:
    """Format requirements dict as readable text for LLM."""
    if isinstance(requirements, str):
        return requirements
    import json
    return json.dumps(requirements, indent=2, default=str)


def _parse_code_blocks(response: str) -> Dict[str, str]:
    """Extract named code blocks from LLM response.

    Tries multiple patterns to handle various LLM output formats:
      1. ```filename.c\\n<content>\\n```
      2. ```c\\n// filename: xxx.c\\n<content>\\n```
      3. Markdown heading (### filename.c) followed by fenced block
      4. Bare filename on its own line followed by content
    """
    files: Dict[str, str] = {}

    # Pattern 1: ```filename.c\n<content>\n``` (standard)
    p1 = re.compile(r"```(\S+\.(?:c|h))\s*\n(.*?)```", re.DOTALL)
    for m in p1.finditer(response):
        files[m.group(1)] = m.group(2).strip()
    if files:
        return files

    # Pattern 2: ```c or ```h with filename in first comment line
    p2 = re.compile(r"```[ch]?\s*\n\s*(?://|/\*)\s*(?:file(?:name)?:?\s*)?(\S+\.(?:c|h)).*?\n(.*?)```", re.DOTALL)
    for m in p2.finditer(response):
        files[m.group(1)] = m.group(2).strip()
    if files:
        return files

    # Pattern 3: ### filename.h or **filename.h** followed by ```<content>```
    p3 = re.compile(r"(?:#{1,4}\s*|(?:\*\*))(\S+\.(?:c|h))(?:\*\*)?\s*\n+```[a-z]*\s*\n(.*?)```", re.DOTALL)
    for m in p3.finditer(response):
        files[m.group(1)] = m.group(2).strip()
    if files:
        return files

    # Pattern 4: Bare filenames on their own line, content until next filename or end
    # Split on lines that look like standalone filenames
    filename_line = re.compile(r"^(\S+\.(?:c|h))\s*$", re.MULTILINE)
    splits = filename_line.split(response)
    # splits = [before_first, filename1, content1, filename2, content2, ...]
    if len(splits) >= 3:
        for i in range(1, len(splits) - 1, 2):
            fname = splits[i].strip()
            content = splits[i + 1].strip()
            # Strip any wrapping backticks the content might have
            content = re.sub(r"^```[a-z]*\s*\n?", "", content)
            content = re.sub(r"\n?```\s*$", "", content)
            if content:
                files[fname] = content.strip()
    if files:
        return files

    return None

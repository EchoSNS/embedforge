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
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from config.llm_config import get_llm
from plugins.base import PluginRegistry

logger = logging.getLogger(__name__)


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

    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry

    def generate(
        self,
        requirements: Dict[str, Any],
        driver_context: str,
        pin_context: str,
        architecture_rules: str,
        reference_context: str = "",
    ) -> TDDResult:
        """
        Run the full TDD generation pipeline.

        Args:
            requirements: structured requirements from the workflow state
            driver_context: SDK driver API info for LLM
            pin_context: validated pin symbols for LLM
            architecture_rules: SDK coding rules for LLM
            reference_context: optional reference project patterns
        """
        # Phase 1: Mock generation
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
        )
        if not mock_result:
            logger.error("TDD Phase 1 failed: %s", mock_err)
            return TDDResult(
                success=False,
                phase=TDDPhase.MOCK_GENERATION,
                errors=[f"Mock generation failed: {mock_err}"],
                error_detail=mock_err,
            )

        # Phase 2: Test generation
        logger.info("TDD Phase 2: Generating tests (mocks: %d files)", len(mock_result))
        mock_summary = "\n".join(f"// {name}" for name in mock_result.keys())
        test_result, test_err = self._invoke_and_parse(
            self._build_test_prompt(architecture_rules),
            (
                f"Generate Unity test files for the following requirements.\n\n"
                f"REQUIREMENTS:\n{_format_requirements(requirements)}\n\n"
                f"AVAILABLE MOCKS:\n{mock_summary}\n\n"
                f"SDK API:\n{driver_context}\n\n"
                f"Write test cases that verify the production code behavior. "
                f"Tests should fail initially (Red phase)."
            ),
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

        # Phase 3: Production code
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
            self._build_production_prompt(architecture_rules), prod_user_prompt
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

    def _invoke_and_parse(self, system_prompt: str, user_prompt: str) -> tuple[Optional[Dict[str, str]], str]:
        """Invoke LLM and parse code blocks. Returns (files, error_detail)."""
        llm = get_llm()
        try:
            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ])
            parsed = _parse_code_blocks(response.content)
            if parsed is None:
                preview = response.content[:300].replace("\n", " ")
                detail = (
                    f"LLM responded but no code blocks (```filename.c ... ```) were found in output. "
                    f"Response preview: {preview}"
                )
                logger.warning("Code block parse failed: %s", detail)
                return None, detail
            return parsed, ""
        except Exception as e:
            detail = f"{type(e).__name__}: {e}"
            logger.error("LLM invocation failed: %s", detail)
            return None, detail

    def _build_mock_prompt(self, rules: str) -> str:
        return (
            "You are an expert embedded C test engineer.\n"
            "Generate mock/stub files for SDK drivers using spy pattern.\n\n"
            "Each mock must:\n"
            "- Include all struct/enum types from the real SDK header\n"
            "- Provide spy counters for each function call\n"
            "- Include a reset function to clear all spies between tests\n\n"
            f"SDK CONVENTIONS:\n{rules}\n\n"
            "Output format: ```filename.h\\n<content>\\n``` for each file."
        )

    def _build_test_prompt(self, rules: str) -> str:
        return (
            "You are an expert embedded C test engineer using Unity test framework.\n"
            "Generate unit test files that verify driver behavior through mocks.\n\n"
            "Test file conventions:\n"
            "- Use TEST_GROUP and TEST macros\n"
            "- setUp() resets all mock spies\n"
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
            "- Follow init/deinit patterns from the SDK\n\n"
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
    """Extract named code blocks from LLM response."""
    files: Dict[str, str] = {}
    pattern = re.compile(r"```(\S+\.(?:c|h))\n(.*?)```", re.DOTALL)
    for match in pattern.finditer(response):
        files[match.group(1)] = match.group(2).strip()
    return files if files else None

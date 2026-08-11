"""
Dynamic Prompt System — generates LLM prompts at runtime from plugin metadata.

Replaces all hardcoded vendor-specific prompt content with template-driven
generation that adapts to whatever SDK plugin is active.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from plugins.base import PluginRegistry

logger = logging.getLogger(__name__)


class DynamicPromptSystem:
    """
    Builds context-aware prompts for each workflow stage by combining:
      - Plugin-provided SDK metadata (drivers, types, patterns)
      - User requirements
      - Reference project analysis
      - Architecture rules
    """

    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry

    def build_codegen_prompt(
        self,
        requirements: Dict[str, Any],
        driver_context: str,
        pin_context: str,
        reference_context: str = "",
    ) -> str:
        """Build the code generation user prompt with full SDK context."""
        rules = self._registry.get_architecture_rules()
        rules_text = rules.get_rules_text()

        sections = [
            "Generate embedded C code for the following requirements.",
            "",
            f"REQUIREMENTS:\n{_format_dict(requirements)}",
            "",
            f"SDK DRIVER API:\n{driver_context}",
            "",
            f"VALIDATED PIN ASSIGNMENTS:\n{pin_context}",
            "",
            f"ARCHITECTURE RULES:\n{rules_text}",
        ]

        if reference_context:
            sections.extend(["", f"REFERENCE PATTERNS:\n{reference_context}"])

        sections.extend([
            "",
            "Generate production-quality .c and .h files following the SDK conventions.",
            "Output format: ```filename.ext\\n<content>\\n``` for each file.",
        ])

        return "\n".join(sections)

    def build_mock_prompt(
        self,
        requirements: Dict[str, Any],
        driver_context: str,
    ) -> str:
        """Build the mock generation prompt."""
        rules = self._registry.get_architecture_rules()
        conventions = rules.get_naming_conventions()

        return (
            f"Generate mock/stub files for unit testing.\n\n"
            f"REQUIREMENTS:\n{_format_dict(requirements)}\n\n"
            f"SDK API:\n{driver_context}\n\n"
            f"NAMING CONVENTIONS:\n{_format_dict(conventions)}\n\n"
            f"Generate mock headers with spy counters for all SDK functions."
        )

    def build_test_prompt(
        self,
        requirements: Dict[str, Any],
        mock_files: Dict[str, str],
        driver_context: str,
    ) -> str:
        """Build the test generation prompt."""
        mock_list = "\n".join(f"  - {name}" for name in mock_files.keys())

        return (
            f"Generate Unity unit tests.\n\n"
            f"REQUIREMENTS:\n{_format_dict(requirements)}\n\n"
            f"AVAILABLE MOCKS:\n{mock_list}\n\n"
            f"SDK API:\n{driver_context}\n\n"
            f"Write tests that verify driver initialization and operation."
        )

    def build_hardware_prompt(
        self,
        requirements: Dict[str, Any],
        board_capabilities: str,
        pin_context: str,
    ) -> str:
        """Build the hardware node prompt for peripheral/pin assignment."""
        return (
            f"Assign hardware peripherals and pins for the requirements.\n\n"
            f"REQUIREMENTS:\n{_format_dict(requirements)}\n\n"
            f"BOARD CAPABILITIES:\n{board_capabilities}\n\n"
            f"AVAILABLE PINS:\n{pin_context}\n\n"
            f"Output a JSON with peripheral assignments, pin mappings, and clock configuration."
        )

    def build_software_arch_prompt(
        self,
        requirements: Dict[str, Any],
        hardware_spec: Dict[str, Any],
        driver_options: str,
    ) -> str:
        """Build the software architecture node prompt for driver selection."""
        return (
            f"Select SDK drivers and define the software architecture.\n\n"
            f"REQUIREMENTS:\n{_format_dict(requirements)}\n\n"
            f"HARDWARE SPEC:\n{_format_dict(hardware_spec)}\n\n"
            f"AVAILABLE DRIVERS:\n{driver_options}\n\n"
            f"Output a JSON with selected drivers, their roles, dependencies, and init order."
        )

    def build_software_detailed_prompt(
        self,
        requirements: Dict[str, Any],
        architecture: Dict[str, Any],
        driver_context: str,
        pin_context: str,
    ) -> str:
        """Build the detailed software design prompt."""
        rules = self._registry.get_architecture_rules()
        rules_text = rules.get_rules_text()

        return (
            f"Create a detailed software design with function-level specifications.\n\n"
            f"REQUIREMENTS:\n{_format_dict(requirements)}\n\n"
            f"ARCHITECTURE:\n{_format_dict(architecture)}\n\n"
            f"SDK API:\n{driver_context}\n\n"
            f"PIN ASSIGNMENTS:\n{pin_context}\n\n"
            f"ARCHITECTURE RULES:\n{rules_text}\n\n"
            f"Output a JSON with function signatures, init sequences, ISR definitions, "
            f"and configuration struct layouts."
        )


def _format_dict(data: Any) -> str:
    if isinstance(data, str):
        return data
    import json
    return json.dumps(data, indent=2, default=str)

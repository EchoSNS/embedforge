"""
Architecture Rules — loads and applies SDK coding conventions from the active plugin.

Provides rule text for LLM prompt injection and post-generation validation.
"""

from __future__ import annotations

import logging
from typing import Dict, List

from plugins.base import ArchitectureRulePack, PluginRegistry

logger = logging.getLogger(__name__)


class ArchitectureRulesService:
    """
    Application-level service for architecture rule enforcement.

    Delegates to the plugin's ArchitectureRulePack, adding formatting
    for different prompt contexts (mock, test, production).
    """

    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry

    @property
    def _rules(self) -> ArchitectureRulePack:
        return self._registry.get_architecture_rules()

    def get_rules_for_prompt(self) -> str:
        return self._rules.get_rules_text()

    def get_init_pattern(self, driver_name: str) -> str:
        return self._rules.get_init_pattern(driver_name)

    def get_naming_conventions(self) -> Dict[str, str]:
        return self._rules.get_naming_conventions()

    def validate(self, code: str) -> List[str]:
        return self._rules.validate_code(code)

    def format_rules_summary(self) -> str:
        """Concise summary suitable for system prompt preamble."""
        conventions = self.get_naming_conventions()
        lines = ["SDK Architecture Rules:"]
        for key, value in conventions.items():
            lines.append(f"  • {key}: {value}")
        return "\n".join(lines)

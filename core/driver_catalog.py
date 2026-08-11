"""
Driver Catalog — resolves SDK drivers from the active plugin's registry.

Wraps the plugin's DriverCatalog interface with caching, fallback logic,
and LLM-friendly output formatting.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from plugins.base import ApiLayer, DriverCatalog, DriverInfo, PluginRegistry

logger = logging.getLogger(__name__)


class DriverCatalogService:
    """
    Application-level driver lookup service.

    Delegates to the active plugin's DriverCatalog while adding:
      - Formatted output for LLM context injection
      - Requirement-to-driver resolution with fallback
      - Peripheral taxonomy helpers
    """

    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry

    @property
    def _catalog(self) -> DriverCatalog:
        return self._registry.get_driver_catalog()

    def list_peripherals(self) -> List[str]:
        return self._catalog.list_peripherals()

    def list_drivers(self, peripheral: str) -> List[DriverInfo]:
        return self._catalog.list_drivers(peripheral)

    def recommend(self, peripheral: str, requirements: Dict[str, Any]) -> Optional[DriverInfo]:
        return self._catalog.recommend_driver(peripheral, requirements)

    def get_driver_context(self, driver_name: str) -> str:
        """
        Build an LLM-ready context string for a driver: functions, types, usage guidance.
        """
        driver = self._catalog.get_driver(driver_name)
        if not driver:
            return f"Driver '{driver_name}' not found in catalog."

        functions = self._catalog.get_driver_functions(driver_name)
        types = self._catalog.get_driver_types(driver_name)

        lines = [
            f"Driver: {driver.name} ({driver.api_layer.value})",
            f"Peripheral: {driver.peripheral}",
            f"Description: {driver.description}",
        ]

        if driver.when_to_use:
            lines.append(f"Use when: {driver.when_to_use}")
        if driver.when_not_to_use:
            lines.append(f"Avoid when: {driver.when_not_to_use}")

        if functions:
            lines.append("\nFunctions:")
            for fn in functions:
                sig = fn.get("signature", fn.get("name", ""))
                lines.append(f"  {sig}")

        if types:
            lines.append("\nTypes:")
            for t in types:
                lines.append(f"  {t.get('name', '')} — {t.get('kind', 'struct')}")

        return "\n".join(lines)

    def format_peripheral_summary(self, peripheral: str) -> str:
        """Format all drivers for a peripheral as an LLM context block."""
        drivers = self.list_drivers(peripheral)
        if not drivers:
            return f"No drivers found for peripheral '{peripheral}'."

        lines = [f"Available {peripheral} drivers:"]
        for d in drivers:
            supersede_note = ""
            if d.superseded_by:
                supersede_note = f" [superseded by {', '.join(d.superseded_by)}]"
            lines.append(f"  • {d.name} ({d.api_layer.value}) — {d.description}{supersede_note}")

        return "\n".join(lines)

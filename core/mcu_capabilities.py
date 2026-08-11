"""
MCU Capabilities — pin and peripheral queries delegated to the active plugin.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from plugins.base import PinCapabilityProvider, PinMapping, PluginRegistry

logger = logging.getLogger(__name__)


class MCUCapabilityService:
    """
    Provides MCU pin/peripheral queries for the workflow nodes.

    Wraps PinCapabilityProvider with convenience methods and
    formatted output for LLM context.
    """

    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry

    @property
    def _provider(self) -> PinCapabilityProvider:
        return self._registry.get_pin_provider()

    def get_pins(self, peripheral: str, function: str = "") -> List[PinMapping]:
        return self._provider.get_available_pins(peripheral, function)

    def validate_pin(self, symbol: str) -> bool:
        return self._provider.validate_pin(symbol)

    def validate_assignments(self, assignments: Dict[str, str]) -> List[str]:
        return self._provider.validate_assignment(assignments)

    def get_pin_patterns(self) -> Dict[str, str]:
        return self._provider.get_pin_patterns()

    def format_available_pins(self, peripheral: str) -> str:
        """Format available pins for LLM context injection."""
        pins = self.get_pins(peripheral)
        if not pins:
            return f"No pins found for peripheral '{peripheral}'."

        lines = [f"Available {peripheral} pins:"]
        for p in pins[:30]:  # limit to avoid context explosion
            lines.append(f"  {p.symbol} — {p.port} pin {p.pin} ({p.function})")
        if len(pins) > 30:
            lines.append(f"  ... and {len(pins) - 30} more")
        return "\n".join(lines)

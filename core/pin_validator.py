"""
Pin Validator — validates pin symbols in generated code against the MCU's capability map.

Catches invalid pin references before compilation, preventing
hard-to-debug linker/undefined-symbol errors.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Set

from plugins.base import PinCapabilityProvider, PluginRegistry

logger = logging.getLogger(__name__)


class PinValidationResult:
    __slots__ = ("valid_pins", "invalid_pins", "warnings")

    def __init__(self) -> None:
        self.valid_pins: List[str] = []
        self.invalid_pins: List[str] = []
        self.warnings: List[str] = []

    @property
    def is_valid(self) -> bool:
        return len(self.invalid_pins) == 0


class PinValidator:
    """
    Validates pin symbols found in generated C code against the active plugin's
    pin capability data.
    """

    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry

    def validate_code(self, code: str) -> PinValidationResult:
        """
        Scan code for physical GPIO pin symbols (e.g., PA5, PB10) and validate
        each against the MCU pin map. Only the 'gpio' pattern is used for
        validation — peripheral function names like USART2_TX are not physical pins.
        """
        provider = self._registry.get_pin_provider()
        patterns = provider.get_pin_patterns()
        result = PinValidationResult()

        found_symbols: Set[str] = set()
        # Only validate physical pin symbols, not peripheral function names
        gpio_pattern = patterns.get("gpio")
        if gpio_pattern:
            for match in re.finditer(gpio_pattern, code):
                found_symbols.add(match.group(0))

        for symbol in sorted(found_symbols):
            if provider.validate_pin(symbol):
                result.valid_pins.append(symbol)
            else:
                result.invalid_pins.append(symbol)

        if result.invalid_pins:
            logger.warning(f"Invalid pins found: {result.invalid_pins}")

        return result

    def get_context_for_prompt(self, peripheral: str) -> str:
        """
        Build validated pin context suitable for injecting into code generation prompts.
        """
        provider = self._registry.get_pin_provider()
        pins = provider.get_available_pins(peripheral)

        if not pins:
            return f"No validated pins available for {peripheral}."

        lines = [f"VALIDATED {peripheral} PINS (use ONLY these in generated code):"]
        for pin in pins[:25]:
            lines.append(f"  {pin.symbol}")

        return "\n".join(lines)

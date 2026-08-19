"""
STM32 Pin Capability Provider — dynamic pin resolution for STM32 MCUs.

Pin data is derived from:
  1. SDK headers (parsed dynamically when SDK path is configured)
  2. Board-specific known pins (minimal bootstrap for LLM context)
  3. Structural validation (any P[A-K]0-15 is valid on STM32)

This avoids maintaining an exhaustive per-MCU pin database.
"""

from __future__ import annotations

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional

from plugins.base import PinCapabilityProvider, PinMapping

logger = logging.getLogger(__name__)

_VALID_PORTS = set("ABCDEFGHIJK")
_PIN_SYMBOL_RE = re.compile(r"^P([A-K])(\d{1,2})$")

# Minimal board-specific pins for LLM context (Nucleo-F446RE defaults)
_BOARD_KNOWN_PINS: List[PinMapping] = [
    # Onboard resources
    PinMapping(symbol="PA5", port="A", pin=5, peripheral="GPIO", function="LED LD2"),
    PinMapping(symbol="PC13", port="C", pin=13, peripheral="GPIO", function="USER_BUTTON B1"),
    # ST-LINK VCP
    PinMapping(symbol="PA2", port="A", pin=2, peripheral="UART", function="USART2_TX", alternate_function=7),
    PinMapping(symbol="PA3", port="A", pin=3, peripheral="UART", function="USART2_RX", alternate_function=7),
    # TIM1 (advanced, complementary capable)
    PinMapping(symbol="PA8", port="A", pin=8, peripheral="PWM", function="TIM1_CH1", alternate_function=1),
    PinMapping(symbol="PA9", port="A", pin=9, peripheral="PWM", function="TIM1_CH2", alternate_function=1),
    PinMapping(symbol="PA10", port="A", pin=10, peripheral="PWM", function="TIM1_CH3", alternate_function=1),
    PinMapping(symbol="PB13", port="B", pin=13, peripheral="PWM", function="TIM1_CH1N", alternate_function=1, is_complementary=True),
    PinMapping(symbol="PB14", port="B", pin=14, peripheral="PWM", function="TIM1_CH2N", alternate_function=1, is_complementary=True),
    PinMapping(symbol="PB15", port="B", pin=15, peripheral="PWM", function="TIM1_CH3N", alternate_function=1, is_complementary=True),
    # TIM2 (general purpose)
    PinMapping(symbol="PA0", port="A", pin=0, peripheral="PWM", function="TIM2_CH1", alternate_function=1),
    PinMapping(symbol="PA1", port="A", pin=1, peripheral="PWM", function="TIM2_CH2", alternate_function=1),
    # ADC1
    PinMapping(symbol="PA0", port="A", pin=0, peripheral="ADC", function="ADC1_IN0"),
    PinMapping(symbol="PA1", port="A", pin=1, peripheral="ADC", function="ADC1_IN1"),
    # SPI1
    PinMapping(symbol="PA5", port="A", pin=5, peripheral="SPI", function="SPI1_SCK", alternate_function=5),
    PinMapping(symbol="PA6", port="A", pin=6, peripheral="SPI", function="SPI1_MISO", alternate_function=5),
    PinMapping(symbol="PA7", port="A", pin=7, peripheral="SPI", function="SPI1_MOSI", alternate_function=5),
    # I2C1
    PinMapping(symbol="PB8", port="B", pin=8, peripheral="I2C", function="I2C1_SCL", alternate_function=4),
    PinMapping(symbol="PB9", port="B", pin=9, peripheral="I2C", function="I2C1_SDA", alternate_function=4),
]


def _is_structurally_valid_pin(symbol: str) -> bool:
    """Check if a symbol matches the STM32 pin naming convention P[A-K][0-15]."""
    m = _PIN_SYMBOL_RE.match(symbol)
    if not m:
        return False
    port = m.group(1)
    pin_num = int(m.group(2))
    return port in _VALID_PORTS and 0 <= pin_num <= 15


class STM32PinProvider(PinCapabilityProvider):
    """
    Pin capability provider for STM32 MCUs.

    Queries the device DB first (if device data has been imported).
    Falls back to bootstrap known-pins + structural validation.
    """

    def __init__(self, sdk_path: Optional[str] = None, device_name: str = "") -> None:
        self._scanned_pins: List[PinMapping] = []
        self._device_name = device_name
        if sdk_path:
            self._scanned_pins = self._scan_pins_from_sdk(sdk_path)

    def _get_db_pins(self, peripheral_type: str) -> List[PinMapping]:
        """Query device DB for pins if device data has been imported."""
        try:
            from core.device_db import get_device_db
            db = get_device_db()
            if not db.has_device_data():
                return []
            device_id = db.find_device(self._device_name) if self._device_name else None
            if device_id is None:
                # Try first available device
                devices = db.list_devices()
                if not devices:
                    return []
                device_id = db.find_device(devices[0]["device"])
            if device_id is None:
                return []
            entries = db.get_pin_mux(device_id, peripheral_type)
            return [
                PinMapping(
                    symbol=e.pin_name, port=e.port, pin=e.pin_number,
                    peripheral=e.peripheral_type, function=e.signal,
                    alternate_function=e.af_number,
                )
                for e in entries
            ]
        except Exception:
            return []

    def get_available_pins(self, peripheral: str, function: str = "") -> List[PinMapping]:
        # Try device DB first (ground truth from CubeMX import)
        db_pins = self._get_db_pins(peripheral)
        if db_pins:
            if function:
                db_pins = [p for p in db_pins if function.upper() in p.function.upper()]
            return db_pins

        # Fallback to bootstrap + scanned pins
        all_pins = _BOARD_KNOWN_PINS + self._scanned_pins
        peripheral_upper = peripheral.upper()
        results = [p for p in all_pins if p.peripheral == peripheral_upper]
        if function:
            results = [p for p in results if function.upper() in p.function.upper()]
        return results

    def validate_pin(self, symbol: str) -> bool:
        return _is_structurally_valid_pin(symbol)

    def validate_assignment(self, assignments: Dict[str, str]) -> List[str]:
        errors: List[str] = []
        used_pins: Dict[str, str] = {}

        for func_name, pin_symbol in assignments.items():
            if not _is_structurally_valid_pin(pin_symbol):
                errors.append(f"Invalid pin '{pin_symbol}' for function '{func_name}'")
                continue
            if pin_symbol in used_pins:
                errors.append(
                    f"Pin conflict: '{pin_symbol}' assigned to both "
                    f"'{used_pins[pin_symbol]}' and '{func_name}'"
                )
            else:
                used_pins[pin_symbol] = func_name

        return errors

    def get_pin_patterns(self) -> Dict[str, str]:
        return {
            "gpio": r"\bP[A-K]\d{1,2}\b",
        }

    @staticmethod
    def _scan_pins_from_sdk(sdk_path: str) -> List[PinMapping]:
        """Parse GPIO AF definitions from SDK headers to enrich pin context."""
        pins: List[PinMapping] = []
        sdk = Path(sdk_path)
        if not sdk.exists():
            return pins

        af_pattern = re.compile(r"#define\s+GPIO_(AF\d+)_(\w+)\s+")
        for header in sdk.rglob("*gpio*ex*.h"):
            try:
                content = header.read_text(encoding="utf-8", errors="ignore")
                for m in af_pattern.finditer(content):
                    af_num = int(m.group(1)[2:])
                    func_name = m.group(2)
                    periph = _guess_peripheral_from_af(func_name)
                    if periph:
                        pins.append(PinMapping(
                            symbol="", port="", pin=0,
                            peripheral=periph,
                            function=func_name,
                            alternate_function=af_num,
                        ))
            except OSError:
                continue

        if pins:
            logger.info("Scanned %d AF definitions from SDK headers", len(pins))
        return pins


def _guess_peripheral_from_af(func_name: str) -> str:
    """Map an AF function name to a peripheral category."""
    name = func_name.upper()
    if "USART" in name or "UART" in name:
        return "UART"
    if "TIM" in name:
        return "PWM"
    if "SPI" in name:
        return "SPI"
    if "I2C" in name:
        return "I2C"
    if "ADC" in name:
        return "ADC"
    if "CAN" in name:
        return "CAN"
    if "DAC" in name:
        return "DAC"
    return ""

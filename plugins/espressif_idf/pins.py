"""ESP32 pin provider — GPIO0-GPIO48 (varies by variant)."""

from __future__ import annotations

import re
from typing import Dict, List

from plugins.base import PinCapabilityProvider, PinMapping

_ESP_PIN_RE = re.compile(r"^GPIO(\d+)$")
# ESP32 max GPIOs by variant
_MAX_GPIO = {"ESP32": 39, "ESP32-S3": 48, "ESP32-C3": 21, "ESP32-C6": 30}


class ESPPinProvider(PinCapabilityProvider):
    """Pin provider for ESP32 — GPIO0 to GPIO48 (variant-dependent)."""

    def get_available_pins(self, peripheral: str, function: str = "") -> List[PinMapping]:
        try:
            from core.device_db import get_device_db
            db = get_device_db()
            if not db.has_device_data():
                return []
            devices = db.list_devices()
            esp = [d for d in devices if "Espressif" in d.get("vendor", "") or "ESP" in d.get("family", "")]
            if not esp:
                return []
            device_id = db.find_device(esp[0]["device"])
            if device_id is None:
                return []
            entries = db.get_pin_mux(device_id, peripheral.upper())
            return [
                PinMapping(symbol=e.pin_name, port=e.port, pin=e.pin_number,
                           peripheral=e.peripheral_type, function=e.signal,
                           alternate_function=e.af_number)
                for e in entries
            ]
        except Exception:
            return []

    def validate_pin(self, symbol: str) -> bool:
        m = _ESP_PIN_RE.match(symbol)
        if not m:
            return False
        num = int(m.group(1))
        return 0 <= num <= 48

    def validate_assignment(self, assignments: Dict[str, str]) -> List[str]:
        errors = []
        used = {}
        for func, pin in assignments.items():
            if not self.validate_pin(pin):
                errors.append(f"Invalid pin '{pin}' for '{func}'")
                continue
            if pin in used:
                errors.append(f"Pin conflict: '{pin}' used by '{used[pin]}' and '{func}'")
            else:
                used[pin] = func
        return errors

    def get_pin_patterns(self) -> Dict[str, str]:
        return {"gpio": r"\bGPIO\d+\b"}

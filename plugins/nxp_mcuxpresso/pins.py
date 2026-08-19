"""NXP pin provider — structural validation for LPC/i.MX RT pin naming."""

from __future__ import annotations

import re
import logging
from typing import Dict, List, Optional

from plugins.base import PinCapabilityProvider, PinMapping

logger = logging.getLogger(__name__)

# NXP uses PIOx_y (LPC) or GPIO_AD_B0_03 (i.MX RT) naming
_LPC_PIN_RE = re.compile(r"^PIO(\d+)_(\d+)$")
_IMXRT_PIN_RE = re.compile(r"^GPIO_(\w+)_(\d+)$")


class NXPPinProvider(PinCapabilityProvider):
    """Pin provider for NXP MCUs — structural validation."""

    def get_available_pins(self, peripheral: str, function: str = "") -> List[PinMapping]:
        # Populated from device DB when imported
        try:
            from core.device_db import get_device_db
            db = get_device_db()
            if not db.has_device_data():
                return []
            devices = db.list_devices()
            nxp_devices = [d for d in devices if d.get("vendor", "").startswith("NXP")]
            if not nxp_devices:
                return []
            device_id = db.find_device(nxp_devices[0]["device"])
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
        return bool(_LPC_PIN_RE.match(symbol) or _IMXRT_PIN_RE.match(symbol))

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
        return {"gpio": r"\bPIO\d+_\d+\b|\bGPIO_\w+_\d+\b"}

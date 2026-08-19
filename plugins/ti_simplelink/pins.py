"""TI pin provider — DIO naming (DIO0-DIO31) for CC26xx; Pxy for MSP432."""
from __future__ import annotations
import re
from typing import Dict, List
from plugins.base import PinCapabilityProvider, PinMapping

_DIO_RE = re.compile(r"^DIO(\d+)$")
_MSP_RE = re.compile(r"^P(\d+)\.(\d+)$")

class TIPinProvider(PinCapabilityProvider):
    def get_available_pins(self, peripheral: str, function: str = "") -> List[PinMapping]:
        try:
            from core.device_db import get_device_db
            db = get_device_db()
            if not db.has_device_data():
                return []
            devices = db.list_devices()
            ti = [d for d in devices if "Texas" in d.get("vendor", "") or "TI" in d.get("vendor", "")]
            if not ti:
                return []
            device_id = db.find_device(ti[0]["device"])
            if device_id is None:
                return []
            entries = db.get_pin_mux(device_id, peripheral.upper())
            return [PinMapping(symbol=e.pin_name, port=e.port, pin=e.pin_number,
                               peripheral=e.peripheral_type, function=e.signal,
                               alternate_function=e.af_number) for e in entries]
        except Exception:
            return []

    def validate_pin(self, symbol: str) -> bool:
        if _DIO_RE.match(symbol):
            return int(_DIO_RE.match(symbol).group(1)) <= 31
        if _MSP_RE.match(symbol):
            return True
        return False

    def validate_assignment(self, assignments: Dict[str, str]) -> List[str]:
        errors, used = [], {}
        for func, pin in assignments.items():
            if not self.validate_pin(pin):
                errors.append(f"Invalid pin '{pin}' for '{func}'")
            elif pin in used:
                errors.append(f"Pin conflict: '{pin}' used by '{used[pin]}' and '{func}'")
            else:
                used[pin] = func
        return errors

    def get_pin_patterns(self) -> Dict[str, str]:
        return {"gpio": r"\bDIO\d+\b|\bP\d+\.\d+\b"}

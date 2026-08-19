"""
iLLD Pin Extractor — parses Infineon AURIX iLLD pin map headers.

iLLD headers contain pin constants like:
  IFX_EXTERN IfxAsclin_Tx_Out IfxAsclin0_TX_P14_0_OUT;
  IFX_EXTERN IfxAsclin_Rx_In  IfxAsclin0_RXA_P14_1_IN;

This extractor parses these patterns into PinMuxEntry records.
Works for TC3xx and TC4xx families.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

from core.device_data import DeviceInfo, PeripheralInstance, PinDirection, PinMuxEntry
from plugins.base import DeviceDataImporter

logger = logging.getLogger(__name__)

# Matches: IfxModule<Instance>_<Signal>_P<port>_<pin>_<DIR>
_PIN_CONST_RE = re.compile(
    r"Ifx(\w+?)(\d+)_(\w+?)_P(\d+)_(\d+)_(INOUT|OUT|IN)",
)

# Simpler pattern for lines like: IfxAsclin0_TX_P14_0_OUT
_PIN_LINE_RE = re.compile(
    r"Ifx(\w+?)(\d+)_(\w+)_P(\d+)_(\d+)_(INOUT|OUT|IN)"
)

_DIR_MAP = {
    "IN": PinDirection.INPUT,
    "OUT": PinDirection.OUTPUT,
    "INOUT": PinDirection.BIDIRECTIONAL,
}


def _classify_module(module: str) -> str:
    """Map iLLD module name to peripheral type."""
    m = module.upper()
    if m in ("ASCLIN",):
        return "UART"
    if m in ("QSPI", "SPI"):
        return "SPI"
    if m in ("I2C",):
        return "I2C"
    if m in ("GTM", "TOM", "ATOM", "CCU6"):
        return "PWM"
    if m in ("VADC", "DSADC", "EVADC"):
        return "ADC"
    if m in ("PORT",):
        return "GPIO"
    if m in ("MULTICAN", "CAN", "MCMCAN"):
        return "CAN"
    if m in ("GETH", "ETH"):
        return "ETHERNET"
    if m in ("STM",):
        return "TIMER"
    if m in ("SENT",):
        return "SENSOR"
    return "OTHER"


class ILLDPinExtractor(DeviceDataImporter):
    """Extracts pin-mux data from AURIX iLLD *_PinMap.h headers."""

    @property
    def source_format(self) -> str:
        return "illd"

    def can_import(self, path: str) -> bool:
        p = Path(path)
        if not p.is_dir():
            return False
        # Detect iLLD structure: look for *_PinMap.h files
        pin_maps = list(p.rglob("*_PinMap.h"))
        if pin_maps:
            return True
        # Also check for iLLD directory marker
        return any(p.rglob("IfxPort.h")) or any(p.rglob("Ifx_Types.h"))

    def list_available_devices(self, path: str) -> List[str]:
        p = Path(path)
        devices = set()
        # Search for TC* directories recursively (e.g., iLLD/TC4DA/Tricore)
        for d in p.rglob("*"):
            if d.is_dir() and re.match(r"TC\d+\w*", d.name, re.IGNORECASE):
                devices.add(d.name)
        # Also check path components for TC device family hints
        for part in p.parts:
            m = re.match(r"(TC\d+\w*)", part, re.IGNORECASE)
            if m:
                devices.add(m.group(1))
        return sorted(devices) if devices else ["AURIX_Device"]

    def import_device(self, path: str, device_name: str = "") -> Optional[DeviceInfo]:
        p = Path(path)
        if not p.is_dir():
            return None

        pin_mux: List[PinMuxEntry] = []
        peripherals: Dict[str, str] = {}

        # Target package-specific PinMap headers (contain actual pin constants)
        pin_map_files = list(p.rglob("*_PinMap_*_COM.h"))
        if not pin_map_files:
            pin_map_files = list(p.rglob("*_PinMap_*.h"))
        if not pin_map_files:
            pin_map_files = list(p.rglob("*_PinMap.h"))

        for header in pin_map_files:
            try:
                content = header.read_text(encoding="utf-8", errors="ignore")
                entries = self._parse_pin_map(content)
                pin_mux.extend(entries)
                for e in entries:
                    if e.peripheral not in peripherals:
                        peripherals[e.peripheral] = e.peripheral_type
            except OSError:
                continue

        periph_list = [
            PeripheralInstance(name=name, peripheral_type=ptype)
            for name, ptype in sorted(peripherals.items())
        ]

        device = device_name or "AURIX_Device"
        info = DeviceInfo(
            vendor="Infineon Technologies",
            family="AURIX",
            device=device,
            package="",
            core="TriCore",
            pin_mux=pin_mux,
            peripherals=periph_list,
            source_file=str(p),
            source_format="illd",
        )

        logger.info("Parsed iLLD %s: %d pin-mux entries, %d peripherals",
                    device, len(pin_mux), len(periph_list))
        return info

    def _parse_pin_map(self, content: str) -> List[PinMuxEntry]:
        """Extract pin constants from a PinMap header."""
        entries: List[PinMuxEntry] = []
        seen = set()

        for match in _PIN_LINE_RE.finditer(content):
            module = match.group(1)
            instance = match.group(2)
            signal = match.group(3)
            port = match.group(4)
            pin = match.group(5)
            direction = match.group(6)

            pin_name = f"P{port}.{pin}"
            periph_name = f"{module}{instance}".upper()
            signal_name = f"{periph_name}_{signal}"
            key = (pin_name, signal_name)

            if key in seen:
                continue
            seen.add(key)

            entries.append(PinMuxEntry(
                pin_name=pin_name,
                port=port,
                pin_number=int(pin),
                af_number=-1,  # AURIX doesn't use AF numbers
                signal=signal_name,
                peripheral=periph_name,
                peripheral_type=_classify_module(module),
                direction=_DIR_MAP.get(direction, PinDirection.BIDIRECTIONAL),
            ))

        return entries

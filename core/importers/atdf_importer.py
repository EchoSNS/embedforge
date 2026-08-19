"""
ATDF Importer — parses Microchip ATDF files for AVR/SAM device data.

ATDF (Atmel/Microchip Device File) is an XML format containing pin-mux,
peripheral instances, register maps, and interrupt vectors for AVR and SAM MCUs.
Located in Microchip toolchain: tools/devices/*.atdf
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional

from core.device_data import DeviceInfo, PeripheralInstance, PinDirection, PinMuxEntry
from plugins.base import DeviceDataImporter

logger = logging.getLogger(__name__)


class ATDFImporter(DeviceDataImporter):
    """Imports device data from Microchip ATDF files."""

    @property
    def source_format(self) -> str:
        return "atdf"

    def can_import(self, path: str) -> bool:
        p = Path(path)
        if p.is_file() and p.suffix.lower() == ".atdf":
            return True
        if p.is_dir():
            return any(p.rglob("*.atdf"))
        return False

    def list_available_devices(self, path: str) -> List[str]:
        p = Path(path)
        if p.is_file() and p.suffix.lower() == ".atdf":
            return [p.stem]
        if p.is_dir():
            return sorted(f.stem for f in p.rglob("*.atdf"))
        return []

    def import_device(self, path: str, device_name: str = "") -> Optional[DeviceInfo]:
        p = Path(path)
        if p.is_file() and p.suffix.lower() == ".atdf":
            atdf_file = p
        elif p.is_dir():
            if device_name:
                candidates = list(p.rglob(f"*{device_name}*.atdf"))
                atdf_file = candidates[0] if candidates else None
            else:
                atdfs = list(p.rglob("*.atdf"))
                atdf_file = atdfs[0] if atdfs else None
            if not atdf_file:
                return None
        else:
            return None

        return self._parse_atdf(atdf_file)

    def _parse_atdf(self, path: Path) -> Optional[DeviceInfo]:
        try:
            tree = ET.parse(path)
        except ET.ParseError as e:
            logger.error("Failed to parse ATDF %s: %s", path, e)
            return None

        root = tree.getroot()
        ns = _detect_ns(root)

        # Device name from <device> element
        devices_elem = root.find(f"{ns}devices")
        device_elem = devices_elem.find(f"{ns}device") if devices_elem is not None else None
        if device_elem is None:
            return None

        name = device_elem.get("name", path.stem)
        family = device_elem.get("family", "")
        architecture = device_elem.get("architecture", "")

        pin_mux: List[PinMuxEntry] = []
        peripherals: List[PeripheralInstance] = []

        # Parse pinouts
        pinouts = root.find(f"{ns}pinouts")
        if pinouts is not None:
            for pinout in pinouts.findall(f"{ns}pinout"):
                for pin in pinout.findall(f"{ns}pin"):
                    pad = pin.get("pad", "")
                    position = pin.get("position", "")
                    if not pad:
                        continue
                    # Parse pad name (e.g., PA02, PB31)
                    pad_match = re.match(r"P([A-Z])(\d+)", pad)
                    if pad_match:
                        port = pad_match.group(1)
                        pin_num = int(pad_match.group(2))
                    else:
                        port = ""
                        pin_num = 0

                    # Find signal mappings for this pin in modules
                    for signal in self._find_pin_signals(root, ns, pad):
                        pin_mux.append(PinMuxEntry(
                            pin_name=pad,
                            port=port,
                            pin_number=pin_num,
                            af_number=signal.get("mux", -1),
                            signal=signal["name"],
                            peripheral=signal["peripheral"],
                            peripheral_type=signal["type"],
                        ))

        # Parse peripheral instances from modules
        modules = root.find(f"{ns}modules")
        if modules is not None:
            for module in modules.findall(f"{ns}module"):
                mod_name = module.get("name", "")
                for instance in module.findall(f"{ns}instance"):
                    inst_name = instance.get("name", mod_name)
                    ptype = _classify_atdf_module(mod_name)
                    peripherals.append(PeripheralInstance(
                        name=inst_name,
                        peripheral_type=ptype,
                    ))

        info = DeviceInfo(
            vendor="Microchip",
            family=family,
            device=name,
            package="",
            core=architecture,
            pin_mux=pin_mux,
            peripherals=peripherals,
            source_file=str(path),
            source_format="atdf",
        )

        logger.info("Parsed ATDF %s: %d pin-mux, %d peripherals", name, len(pin_mux), len(peripherals))
        return info

    def _find_pin_signals(self, root: ET.Element, ns: str, pad: str) -> List[dict]:
        """Find all peripheral signals mapped to a pad via pinmux groups."""
        signals = []
        modules = root.find(f"{ns}modules")
        if modules is None:
            return signals

        for module in modules.findall(f"{ns}module"):
            mod_name = module.get("name", "")
            for instance in module.findall(f"{ns}instance"):
                inst_name = instance.get("name", mod_name)
                for signal_group in instance.findall(f"{ns}signals"):
                    for signal in signal_group.findall(f"{ns}signal"):
                        if signal.get("pad") == pad:
                            sig_name = signal.get("function", signal.get("group", ""))
                            mux = -1
                            mux_attr = signal.get("index", "")
                            if mux_attr.isdigit():
                                mux = int(mux_attr)
                            signals.append({
                                "name": f"{inst_name}_{sig_name}" if sig_name else inst_name,
                                "peripheral": inst_name,
                                "type": _classify_atdf_module(mod_name),
                                "mux": mux,
                            })
        return signals


def _detect_ns(root: ET.Element) -> str:
    if root.tag.startswith("{"):
        return root.tag.split("}")[0] + "}"
    return ""


def _classify_atdf_module(name: str) -> str:
    n = name.upper()
    if "SERCOM" in n or "USART" in n or "UART" in n:
        return "UART"
    if "TC" in n or "TCC" in n or "TIMER" in n:
        return "PWM"
    if "SPI" in n:
        return "SPI"
    if "I2C" in n or "TWI" in n:
        return "I2C"
    if "ADC" in n:
        return "ADC"
    if "DAC" in n:
        return "DAC"
    if "CAN" in n:
        return "CAN"
    if "PORT" in n or "GPIO" in n:
        return "GPIO"
    return "OTHER"

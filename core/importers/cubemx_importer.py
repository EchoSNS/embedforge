"""
CubeMX Importer — parses STM32CubeMX internal database for pin-AF tables.

STM32CubeMX stores complete pin-to-alternate-function mapping in XML files:
  <CubeMX_install>/db/mcu/<DeviceName>.xml

Each file contains every pin, every AF, and every signal for that exact
MCU device + package combination.
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional

from core.device_data import DeviceInfo, PeripheralInstance, PinDirection, PinMuxEntry
from plugins.base import DeviceDataImporter

logger = logging.getLogger(__name__)

# Map CubeMX signal prefixes to our peripheral type categories
_SIGNAL_TYPE_MAP = {
    "USART": "UART", "UART": "UART", "LPUART": "UART",
    "TIM": "PWM", "LPTIM": "PWM", "HRTIM": "PWM",
    "SPI": "SPI", "QUADSPI": "SPI", "OCTOSPI": "SPI",
    "I2C": "I2C", "FMPI2C": "I2C",
    "ADC": "ADC",
    "DAC": "DAC",
    "CAN": "CAN", "FDCAN": "CAN",
    "SAI": "AUDIO", "I2S": "AUDIO",
    "USB": "USB", "USB_OTG": "USB",
    "ETH": "ETHERNET",
    "SDMMC": "SDIO", "SDIO": "SDIO",
    "DCMI": "CAMERA",
    "COMP": "COMPARATOR",
    "OPAMP": "OPAMP",
    "RTC": "RTC",
    "GPIO": "GPIO",
}


def _classify_signal(signal_name: str) -> str:
    """Determine peripheral type from signal name."""
    name = signal_name.upper()
    for prefix, ptype in _SIGNAL_TYPE_MAP.items():
        if name.startswith(prefix):
            return ptype
    if "GPIO" in name or name.startswith("P") and len(name) <= 5:
        return "GPIO"
    return "OTHER"


def _extract_peripheral_name(signal_name: str) -> str:
    """Extract peripheral instance from signal (e.g. 'USART2_TX' → 'USART2')."""
    m = re.match(r"([A-Z]+\d*)", signal_name)
    return m.group(1) if m else signal_name


def _signal_direction(signal_name: str) -> PinDirection:
    """Infer direction from signal name suffix."""
    name = signal_name.upper()
    if name.endswith("_TX") or name.endswith("_MOSI") or name.endswith("_OUT"):
        return PinDirection.OUTPUT
    if name.endswith("_RX") or name.endswith("_MISO") or name.endswith("_IN"):
        return PinDirection.INPUT
    if "ADC" in name or "DAC" in name or "COMP" in name:
        return PinDirection.ANALOG
    return PinDirection.BIDIRECTIONAL


def _parse_gpio_modes(modes_path: Path) -> Dict[str, int]:
    """Parse a GPIO-*_Modes.xml file to extract signal → AF number mapping."""
    af_map: Dict[str, int] = {}
    try:
        tree = ET.parse(modes_path)
        root = tree.getroot()
        ns = ""
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0] + "}"

        for pin_signal in root.iter(f"{ns}PinSignal") if ns else root.iter("PinSignal"):
            sig_name = pin_signal.get("Name", "")
            if not sig_name:
                continue
            for pv in pin_signal.iter(f"{ns}PossibleValue") if ns else pin_signal.iter("PossibleValue"):
                if pv.text:
                    af_match = re.match(r"GPIO_AF(\d+)_", pv.text)
                    if af_match:
                        af_map[sig_name] = int(af_match.group(1))
                        break
    except (ET.ParseError, OSError) as e:
        logger.debug("Failed to parse GPIO modes %s: %s", modes_path, e)
    return af_map


class CubeMXImporter(DeviceDataImporter):
    """Imports device data from STM32CubeMX XML database."""

    @property
    def source_format(self) -> str:
        return "cubemx"

    def can_import(self, path: str) -> bool:
        p = Path(path)
        # Accept either the db/mcu directory or a specific .xml file
        if p.is_file() and p.suffix == ".xml":
            return self._is_cubemx_device_xml(p)
        if p.is_dir():
            # Check for db/mcu subdirectory structure
            mcu_dir = p / "db" / "mcu" if not p.name == "mcu" else p
            return mcu_dir.exists() and any(mcu_dir.glob("STM32*.xml"))
        return False

    def list_available_devices(self, path: str) -> List[str]:
        mcu_dir = self._resolve_mcu_dir(path)
        if not mcu_dir:
            return []
        devices = []
        for xml_file in sorted(mcu_dir.glob("STM32*.xml")):
            # Skip family overview files (they have different structure)
            if "x" not in xml_file.stem.lower():
                devices.append(xml_file.stem)
            else:
                devices.append(xml_file.stem)
        return devices

    def import_device(self, path: str, device_name: str = "") -> Optional[DeviceInfo]:
        """Import a single device from CubeMX database."""
        p = Path(path)

        if p.is_file() and p.suffix == ".xml":
            xml_path = p
        else:
            mcu_dir = self._resolve_mcu_dir(path)
            if not mcu_dir or not device_name:
                logger.error("Must specify device_name when path is a directory")
                return None
            xml_path = mcu_dir / f"{device_name}.xml"
            if not xml_path.exists():
                # CubeMX groups variants like STM32F446R(C-E)Tx.xml — search for partial match
                for f in sorted(mcu_dir.glob("*.xml")):
                    stem = f.stem
                    # Expand grouped names: STM32F446R(C-E)Tx matches STM32F446RETx
                    expanded = re.sub(r"\(([^)]+)\)", lambda m: f"[{m.group(1).replace('-', '')}]", stem)
                    if re.fullmatch(expanded.replace("x", "."), device_name, re.IGNORECASE):
                        xml_path = f
                        break
                    # Also try simple substring containment
                    if device_name.upper()[:10] in stem.upper():
                        xml_path = f
                        break

        if not xml_path.exists():
            logger.error("Device XML not found: %s", xml_path)
            return None

        return self._parse_device_xml(xml_path)

    def _parse_device_xml(self, xml_path: Path) -> Optional[DeviceInfo]:
        """Parse a CubeMX MCU XML file into DeviceInfo."""
        try:
            tree = ET.parse(xml_path)
        except ET.ParseError as e:
            logger.error("Failed to parse %s: %s", xml_path, e)
            return None

        root = tree.getroot()

        # Detect XML namespace (CubeMX uses xmlns="http://mcd.rou.st.com/...")
        ns = ""
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0] + "}"

        # Extract device metadata
        device_name = root.get("RefName", xml_path.stem)
        package = root.get("Package", "")
        family = root.get("Family", "")

        # Core is a child element in newer CubeMX versions
        core_elem = root.find(f"{ns}Core")
        core = core_elem.text.strip() if core_elem is not None and core_elem.text else root.get("Core", "")

        # Determine max frequency
        max_freq = 0
        freq_elem = root.find(f".//{ns}Frequency")
        if freq_elem is not None and freq_elem.text:
            try:
                max_freq = int(float(freq_elem.text) * 1_000_000)
            except ValueError:
                pass

        pin_mux_entries: List[PinMuxEntry] = []
        peripheral_set: dict = {}

        # Parse IP elements for peripheral instances
        for ip_elem in root.findall(f"{ns}IP"):
            inst_name = ip_elem.get("InstanceName", "")
            ip_name = ip_elem.get("Name", "")
            if inst_name and ip_name:
                ptype = _classify_signal(inst_name)
                if ptype != "OTHER":
                    peripheral_set[inst_name] = ptype

        # Load AF number mapping from GPIO modes file
        af_map = self._load_af_map(xml_path)

        # Parse pin elements
        for pin_elem in root.findall(f".//{ns}Pin"):
            pin_name = pin_elem.get("Name", "")
            # Clean pin names like "PC14-OSCX_IN(PC14)" → "PC14"
            port_match = re.match(r"P([A-K])(\d+)", pin_name)
            if not port_match:
                continue

            port = port_match.group(1)
            pin_num = int(port_match.group(2))

            # Each pin has Signal children
            for signal_elem in pin_elem.findall(f"{ns}Signal"):
                signal_name = signal_elem.get("Name", "")
                if not signal_name or signal_name == "GPIO":
                    continue

                periph_type = _classify_signal(signal_name)
                periph_name = _extract_peripheral_name(signal_name)
                direction = _signal_direction(signal_name)

                # Look up AF number from GPIO modes file
                af_num = af_map.get(signal_name, -1)

                pin_mux_entries.append(PinMuxEntry(
                    pin_name=port_match.group(0),
                    port=port,
                    pin_number=pin_num,
                    af_number=af_num,
                    signal=signal_name,
                    peripheral=periph_name,
                    peripheral_type=periph_type,
                    direction=direction,
                ))

                if periph_name not in peripheral_set:
                    peripheral_set[periph_name] = periph_type

        # Build peripheral instances
        peripherals = [
            PeripheralInstance(name=name, peripheral_type=ptype)
            for name, ptype in sorted(peripheral_set.items())
        ]

        info = DeviceInfo(
            vendor="STMicroelectronics",
            family=family or self._guess_family(device_name),
            device=device_name,
            package=package,
            core=core,
            max_clock_hz=max_freq,
            pin_mux=pin_mux_entries,
            peripherals=peripherals,
            source_file=str(xml_path),
            source_format="cubemx",
        )

        logger.info("Parsed CubeMX device %s: %d pin-mux entries, %d peripherals",
                    device_name, len(pin_mux_entries), len(peripherals))
        return info

    @staticmethod
    def _resolve_mcu_dir(path: str) -> Optional[Path]:
        """Find the db/mcu directory from various input paths."""
        p = Path(path)
        if p.name == "mcu" and p.is_dir():
            return p
        mcu_dir = p / "db" / "mcu"
        if mcu_dir.exists():
            return mcu_dir
        # Try parent paths (user might point to CubeMX root)
        for parent in [p, p.parent, p.parent.parent]:
            candidate = parent / "db" / "mcu"
            if candidate.exists():
                return candidate
        return None

    @staticmethod
    def _is_cubemx_device_xml(path: Path) -> bool:
        """Quick check if a file looks like a CubeMX device XML."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                header = f.read(500)
            return "Mcu" in header and ("RefName" in header or "Pin" in header)
        except OSError:
            return False

    @staticmethod
    def _load_af_map(device_xml_path: Path) -> Dict[str, int]:
        """Load signal → AF number mapping from the GPIO modes XML file.

        CubeMX stores AF numbers in db/mcu/IP/GPIO-<family>_Modes.xml
        as <PinSignal Name="USART2_TX"><PossibleValue>GPIO_AF1_USART2</PossibleValue>
        """
        af_map: Dict[str, int] = {}
        ip_dir = device_xml_path.parent / "IP"
        if not ip_dir.exists():
            return af_map

        # Find matching GPIO modes file from the device's GPIO IP version
        try:
            tree = ET.parse(device_xml_path)
            root = tree.getroot()
            ns = ""
            if root.tag.startswith("{"):
                ns = root.tag.split("}")[0] + "}"

            gpio_version = ""
            for ip in root.findall(f"{ns}IP"):
                if ip.get("Name") == "GPIO":
                    gpio_version = ip.get("Version", "")
                    break

            if gpio_version:
                modes_file = ip_dir / f"GPIO-{gpio_version}_Modes.xml"
                if modes_file.exists():
                    return _parse_gpio_modes(modes_file)

            # Fallback: search for any matching GPIO file by family
            family_match = re.match(r"(STM32\w+)", device_xml_path.stem)
            if family_match:
                for gf in ip_dir.glob("GPIO-*_Modes.xml"):
                    if any(part in gf.stem for part in [family_match.group(1)[:7], family_match.group(1)[:9]]):
                        return _parse_gpio_modes(gf)

        except (ET.ParseError, OSError):
            pass

        return af_map

    @staticmethod
    def _guess_family(device_name: str) -> str:
        """Guess STM32 family from device name."""
        m = re.match(r"(STM32[A-Z]\d)", device_name)
        return m.group(1) if m else "STM32"

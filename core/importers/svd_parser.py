"""
SVD Parser — extracts peripheral register maps from CMSIS-SVD XML files.

SVD (System View Description) files describe the complete register layout
of an MCU: peripherals, registers, bit fields, interrupts, and base addresses.
Available for virtually all ARM Cortex-M devices via CMSIS Packs.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.device_data import (
    DeviceInfo,
    PeripheralInstance,
    PinMuxEntry,
    Register,
    RegisterField,
)
from plugins.base import DeviceDataImporter

logger = logging.getLogger(__name__)


class SVDParser(DeviceDataImporter):
    """Parses CMSIS-SVD XML files for register and peripheral data."""

    @property
    def source_format(self) -> str:
        return "svd"

    def can_import(self, path: str) -> bool:
        p = Path(path)
        if p.is_file() and p.suffix.lower() == ".svd":
            return True
        if p.is_dir():
            return any(p.rglob("*.svd"))
        return False

    def list_available_devices(self, path: str) -> List[str]:
        p = Path(path)
        if p.is_file() and p.suffix.lower() == ".svd":
            return [p.stem]
        if p.is_dir():
            return [f.stem for f in sorted(p.rglob("*.svd"))]
        return []

    def import_device(self, path: str, device_name: str = "") -> Optional[DeviceInfo]:
        p = Path(path)
        if p.is_file():
            svd_file = p
        elif p.is_dir():
            if device_name:
                candidates = list(p.rglob(f"{device_name}*.svd"))
                svd_file = candidates[0] if candidates else None
            else:
                svds = list(p.rglob("*.svd"))
                svd_file = svds[0] if svds else None
            if not svd_file:
                logger.error("No SVD file found at %s", path)
                return None
        else:
            return None

        return self._parse_svd(svd_file)

    def _parse_svd(self, svd_path: Path) -> Optional[DeviceInfo]:
        """Parse an SVD file into a DeviceInfo with register maps."""
        try:
            tree = ET.parse(svd_path)
        except ET.ParseError as e:
            logger.error("Failed to parse SVD %s: %s", svd_path, e)
            return None

        root = tree.getroot()
        ns = _detect_namespace(root)

        # Device metadata
        name = _text(root, "name", ns) or svd_path.stem
        vendor = _text(root, "vendor", ns) or ""
        description = _text(root, "description", ns) or ""
        series = _text(root, "series", ns) or ""

        # CPU info
        cpu_elem = root.find(f"{ns}cpu") if ns else root.find("cpu")
        core = ""
        if cpu_elem is not None:
            core = _text(cpu_elem, "name", ns) or ""

        peripherals_list: List[PeripheralInstance] = []
        registers_map: Dict[str, List[Register]] = {}

        # Parse peripherals
        periphs_elem = root.find(f"{ns}peripherals") if ns else root.find("peripherals")
        if periphs_elem is None:
            logger.warning("No <peripherals> element in %s", svd_path)
            return DeviceInfo(
                vendor=vendor, family=series, device=name, package="",
                core=core, source_file=str(svd_path), source_format="svd",
            )

        for periph_elem in periphs_elem.findall(f"{ns}peripheral") if ns else periphs_elem.findall("peripheral"):
            periph_name = _text(periph_elem, "name", ns) or "UNKNOWN"
            base_addr_str = _text(periph_elem, "baseAddress", ns) or "0"
            base_addr = _parse_int(base_addr_str)

            # Check for derivedFrom (peripheral inherits from another)
            derived = periph_elem.get("derivedFrom", "")

            # Classify peripheral type
            periph_type = _classify_peripheral(periph_name)

            # Extract interrupt info
            irq_names = []
            for irq_elem in (periph_elem.findall(f"{ns}interrupt") if ns else periph_elem.findall("interrupt")):
                irq_name = _text(irq_elem, "name", ns)
                if irq_name:
                    irq_names.append(irq_name)

            peripherals_list.append(PeripheralInstance(
                name=periph_name,
                peripheral_type=periph_type,
                base_address=base_addr,
                irq_names=tuple(irq_names),
            ))

            # Parse registers
            regs = self._parse_registers(periph_elem, ns, base_addr)
            if regs:
                registers_map[periph_name] = regs
            elif derived and derived in registers_map:
                # Inherit registers from derived peripheral
                registers_map[periph_name] = registers_map[derived]

        info = DeviceInfo(
            vendor=vendor,
            family=series,
            device=name,
            package="",
            core=core,
            peripherals=peripherals_list,
            registers=registers_map,
            source_file=str(svd_path),
            source_format="svd",
        )

        logger.info("Parsed SVD %s: %d peripherals, %d register groups",
                    name, len(peripherals_list), len(registers_map))
        return info

    def _parse_registers(self, periph_elem: ET.Element, ns: str, base_addr: int) -> List[Register]:
        """Extract registers from a peripheral element."""
        registers: List[Register] = []

        regs_elem = periph_elem.find(f"{ns}registers") if ns else periph_elem.find("registers")
        if regs_elem is None:
            return registers

        for reg_elem in (regs_elem.findall(f"{ns}register") if ns else regs_elem.findall("register")):
            reg_name = _text(reg_elem, "name", ns) or "UNKNOWN"
            offset = _parse_int(_text(reg_elem, "addressOffset", ns) or "0")
            size = _parse_int(_text(reg_elem, "size", ns) or "32")
            access = _text(reg_elem, "access", ns) or "read-write"
            reset_val = _parse_int(_text(reg_elem, "resetValue", ns) or "0")
            desc = _text(reg_elem, "description", ns) or ""

            fields = self._parse_fields(reg_elem, ns)

            registers.append(Register(
                name=reg_name,
                offset=offset,
                size=size,
                access=access,
                description=desc,
                reset_value=reset_val,
                fields=tuple(fields),
            ))

        return registers

    def _parse_fields(self, reg_elem: ET.Element, ns: str) -> List[RegisterField]:
        """Extract bit fields from a register element."""
        fields: List[RegisterField] = []

        fields_elem = reg_elem.find(f"{ns}fields") if ns else reg_elem.find("fields")
        if fields_elem is None:
            return fields

        for field_elem in (fields_elem.findall(f"{ns}field") if ns else fields_elem.findall("field")):
            field_name = _text(field_elem, "name", ns) or "UNKNOWN"
            bit_offset = _parse_int(_text(field_elem, "bitOffset", ns) or "0")
            bit_width = _parse_int(_text(field_elem, "bitWidth", ns) or "1")

            # Some SVDs use lsb/msb instead of bitOffset/bitWidth
            if bit_width == 1 and not (_text(field_elem, "bitWidth", ns)):
                lsb = _text(field_elem, "lsb", ns)
                msb = _text(field_elem, "msb", ns)
                if lsb and msb:
                    bit_offset = _parse_int(lsb)
                    bit_width = _parse_int(msb) - bit_offset + 1

            access = _text(field_elem, "access", ns) or "read-write"
            desc = _text(field_elem, "description", ns) or ""

            fields.append(RegisterField(
                name=field_name,
                bit_offset=bit_offset,
                bit_width=bit_width,
                access=access,
                description=desc,
            ))

        return fields


# ─── Helpers ────────────────────────────────────────────────────────────────

def _detect_namespace(root: ET.Element) -> str:
    """Detect XML namespace from root element tag."""
    if root.tag.startswith("{"):
        return root.tag.split("}")[0] + "}"
    return ""


def _text(parent: ET.Element, tag: str, ns: str) -> Optional[str]:
    """Get text content of a child element."""
    elem = parent.find(f"{ns}{tag}") if ns else parent.find(tag)
    if elem is not None and elem.text:
        return elem.text.strip()
    return None


def _parse_int(value: str) -> int:
    """Parse integer from SVD (supports hex 0x prefix and # prefix)."""
    if not value:
        return 0
    value = value.strip().lower()
    if value.startswith("0x") or value.startswith("#"):
        return int(value.replace("#", "0x"), 16)
    try:
        return int(value)
    except ValueError:
        return 0


def _classify_peripheral(name: str) -> str:
    """Map SVD peripheral name to a type category."""
    n = name.upper()
    if any(n.startswith(p) for p in ("USART", "UART", "LPUART")):
        return "UART"
    if any(n.startswith(p) for p in ("TIM", "LPTIM", "HRTIM")):
        return "PWM"
    if n.startswith("SPI") or "QSPI" in n:
        return "SPI"
    if n.startswith("I2C") or n.startswith("FMPI2C"):
        return "I2C"
    if n.startswith("ADC"):
        return "ADC"
    if n.startswith("DAC"):
        return "DAC"
    if any(n.startswith(p) for p in ("CAN", "FDCAN")):
        return "CAN"
    if n.startswith("GPIO"):
        return "GPIO"
    if any(n.startswith(p) for p in ("DMA", "BDMA", "MDMA")):
        return "DMA"
    if "USB" in n:
        return "USB"
    if n.startswith("ETH"):
        return "ETHERNET"
    if n.startswith("RCC"):
        return "RCC"
    if n.startswith("PWR"):
        return "POWER"
    if n.startswith("FLASH"):
        return "FLASH"
    if n.startswith("RTC"):
        return "RTC"
    if any(n.startswith(p) for p in ("SDMMC", "SDIO")):
        return "SDIO"
    if n.startswith("IWDG") or n.startswith("WWDG"):
        return "WATCHDOG"
    if any(n.startswith(p) for p in ("SAI", "I2S")):
        return "AUDIO"
    if n.startswith("DCMI"):
        return "CAMERA"
    if n.startswith("EXTI"):
        return "INTERRUPT"
    if n.startswith("SYSCFG"):
        return "SYSTEM"
    if n.startswith("NVIC") or n.startswith("SCB"):
        return "CORE"
    return "OTHER"

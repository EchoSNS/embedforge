"""
Auto-Discovery — detect installed SDKs, toolchains, and device data sources.

Scans known install paths and environment variables to find:
  - STM32CubeMX (pin-mux database)
  - NXP MCUXpresso SDK
  - Nordic nRF Connect SDK / nRF5 SDK
  - ESP-IDF
  - Microchip MPLAB X / XC compilers
  - ARM GCC, cppcheck, pyOCD
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredTool:
    """A detected SDK or toolchain installation."""

    name: str
    kind: str           # "sdk", "toolchain", "device_data", "tool"
    path: str
    version: str = ""
    vendor: str = ""
    importable: bool = False  # Can we import device data from this?


def discover_all() -> List[DiscoveredTool]:
    """Run all discovery probes and return findings."""
    results: List[DiscoveredTool] = []
    results.extend(_discover_toolchains())
    results.extend(_discover_stm32cubemx())
    results.extend(_discover_nxp())
    results.extend(_discover_nordic())
    results.extend(_discover_esp_idf())
    results.extend(_discover_microchip())
    results.extend(_discover_infineon())
    results.extend(_discover_renesas())
    results.extend(_discover_ti())
    results.extend(_discover_silabs())
    results.extend(_discover_tools())
    return results


def _discover_toolchains() -> List[DiscoveredTool]:
    found = []
    # ARM GCC
    gcc = shutil.which("arm-none-eabi-gcc")
    if gcc:
        found.append(DiscoveredTool(name="ARM GCC", kind="toolchain", path=gcc, vendor="ARM"))

    # Xtensa (ESP32)
    xtensa = shutil.which("xtensa-esp32-elf-gcc")
    if xtensa:
        found.append(DiscoveredTool(name="Xtensa ESP32 GCC", kind="toolchain", path=xtensa, vendor="Espressif"))

    # RISC-V ESP32-C3
    riscv = shutil.which("riscv32-esp-elf-gcc")
    if riscv:
        found.append(DiscoveredTool(name="RISC-V ESP GCC", kind="toolchain", path=riscv, vendor="Espressif"))

    # AVR GCC
    avrgcc = shutil.which("avr-gcc")
    if avrgcc:
        found.append(DiscoveredTool(name="AVR GCC", kind="toolchain", path=avrgcc, vendor="Microchip"))

    return found


def _discover_stm32cubemx() -> List[DiscoveredTool]:
    found = []
    candidates = []

    if platform.system() == "Windows":
        candidates = [
            Path(os.environ.get("PROGRAMFILES", "")) / "STMicroelectronics" / "STM32Cube" / "STM32CubeMX",
            Path(os.environ.get("LOCALAPPDATA", "")) / "STMicroelectronics" / "STM32Cube" / "STM32CubeMX",
            Path("C:/ST/STM32CubeMX"),
        ]
    else:
        candidates = [
            Path.home() / "STM32CubeMX",
            Path("/opt/st/stm32cubemx"),
            Path("/usr/local/STMicroelectronics/STM32Cube/STM32CubeMX"),
        ]

    # Check env var
    env_path = os.environ.get("STM32CUBEMX_PATH", "")
    if env_path:
        candidates.insert(0, Path(env_path))

    for p in candidates:
        mcu_db = p / "db" / "mcu"
        if mcu_db.exists():
            count = len(list(mcu_db.glob("STM32*.xml")))
            found.append(DiscoveredTool(
                name="STM32CubeMX",
                kind="device_data",
                path=str(p),
                vendor="STMicroelectronics",
                version=f"{count} device files",
                importable=True,
            ))
            break

    return found


def _discover_nxp() -> List[DiscoveredTool]:
    found = []
    sdk = os.environ.get("MCUXPRESSO_SDK_PATH", "")
    if sdk and Path(sdk).exists():
        found.append(DiscoveredTool(
            name="MCUXpresso SDK", kind="sdk", path=sdk, vendor="NXP", importable=True
        ))
    return found


def _discover_nordic() -> List[DiscoveredTool]:
    found = []
    ncs = os.environ.get("NRF_SDK_PATH", "") or os.environ.get("ZEPHYR_BASE", "")
    if ncs and Path(ncs).exists():
        found.append(DiscoveredTool(
            name="nRF Connect SDK", kind="sdk", path=ncs, vendor="Nordic"
        ))

    # Check for nRF Command Line Tools
    nrfjprog = shutil.which("nrfjprog")
    if nrfjprog:
        found.append(DiscoveredTool(name="nRF Command Line Tools", kind="tool", path=nrfjprog, vendor="Nordic"))

    return found


def _discover_esp_idf() -> List[DiscoveredTool]:
    found = []
    idf = os.environ.get("IDF_PATH", "")
    if idf and Path(idf).exists():
        found.append(DiscoveredTool(
            name="ESP-IDF", kind="sdk", path=idf, vendor="Espressif"
        ))
    else:
        # Check common paths
        candidates = [
            Path.home() / "esp" / "esp-idf",
            Path("C:/Espressif/frameworks/esp-idf"),
        ]
        for p in candidates:
            if p.exists():
                found.append(DiscoveredTool(name="ESP-IDF", kind="sdk", path=str(p), vendor="Espressif"))
                break

    idf_py = shutil.which("idf.py")
    if idf_py:
        found.append(DiscoveredTool(name="idf.py", kind="tool", path=idf_py, vendor="Espressif"))

    return found


def _discover_microchip() -> List[DiscoveredTool]:
    found = []
    # MPLAB X IDE device packs contain ATDF files
    candidates = []
    if platform.system() == "Windows":
        candidates = [
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microchip" / "MPLABX",
            Path("C:/Program Files/Microchip/MPLABX"),
        ]
    else:
        candidates = [
            Path("/opt/microchip/mplabx"),
            Path("/Applications/microchip/mplabx"),
        ]

    for p in candidates:
        packs_dir = p / "packs"
        if packs_dir.exists():
            atdf_count = len(list(packs_dir.rglob("*.atdf")))
            if atdf_count:
                found.append(DiscoveredTool(
                    name="MPLAB X Device Packs",
                    kind="device_data",
                    path=str(packs_dir),
                    vendor="Microchip",
                    version=f"{atdf_count} ATDF files",
                    importable=True,
                ))
                break

    return found


def _discover_tools() -> List[DiscoveredTool]:
    found = []
    cppcheck = shutil.which("cppcheck")
    if cppcheck:
        found.append(DiscoveredTool(name="cppcheck", kind="tool", path=cppcheck))

    pyocd = shutil.which("pyocd")
    if pyocd:
        found.append(DiscoveredTool(name="pyOCD", kind="tool", path=pyocd))

    openocd = shutil.which("openocd")
    if openocd:
        found.append(DiscoveredTool(name="OpenOCD", kind="tool", path=openocd))

    jlink = shutil.which("JLinkExe") or shutil.which("JLink")
    if jlink:
        found.append(DiscoveredTool(name="SEGGER J-Link", kind="tool", path=jlink))

    return found


def _discover_infineon() -> List[DiscoveredTool]:
    found = []
    mtb = os.environ.get("MTB_PATH", "") or os.environ.get("CY_TOOLS_PATHS", "")
    if mtb and Path(mtb).exists():
        found.append(DiscoveredTool(name="ModusToolbox", kind="sdk", path=mtb, vendor="Infineon"))
    # Common install paths
    for p in [Path("C:/Users") / os.getlogin() / "ModusToolbox" if platform.system() == "Windows" else Path.home() / "ModusToolbox"]:
        if p.exists():
            found.append(DiscoveredTool(name="ModusToolbox", kind="sdk", path=str(p), vendor="Infineon"))
            break
    return found


def _discover_renesas() -> List[DiscoveredTool]:
    found = []
    fsp = os.environ.get("FSP_PATH", "")
    if fsp and Path(fsp).exists():
        found.append(DiscoveredTool(name="Renesas FSP", kind="sdk", path=fsp, vendor="Renesas"))
    e2 = shutil.which("e2studio")
    if e2:
        found.append(DiscoveredTool(name="e2 studio", kind="tool", path=e2, vendor="Renesas"))
    return found


def _discover_ti() -> List[DiscoveredTool]:
    found = []
    sdk = os.environ.get("SIMPLELINK_SDK_PATH", "")
    if sdk and Path(sdk).exists():
        found.append(DiscoveredTool(name="SimpleLink SDK", kind="sdk", path=sdk, vendor="Texas Instruments"))
    ccs = shutil.which("ccstudio")
    if ccs:
        found.append(DiscoveredTool(name="Code Composer Studio", kind="tool", path=ccs, vendor="Texas Instruments"))
    return found


def _discover_silabs() -> List[DiscoveredTool]:
    found = []
    gsdk = os.environ.get("GSDK_PATH", "") or os.environ.get("SL_SDK_PATH", "")
    if gsdk and Path(gsdk).exists():
        found.append(DiscoveredTool(name="Gecko SDK", kind="sdk", path=gsdk, vendor="Silicon Labs"))
    simplicity = shutil.which("slc") or shutil.which("commander")
    if simplicity:
        found.append(DiscoveredTool(name="Simplicity Commander", kind="tool", path=simplicity, vendor="Silicon Labs"))
    return found

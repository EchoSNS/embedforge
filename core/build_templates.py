"""
Build Template Generator — creates CMakeLists.txt / Makefile from generated code.

Produces a ready-to-build project structure for the generated firmware files.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def generate_cmake(
    project_name: str,
    source_files: List[str],
    target_mcu: str,
    sdk_include_paths: List[str],
    linker_script: str = "",
) -> str:
    """Generate a CMakeLists.txt for the embedded project."""
    sources = "\n    ".join(source_files)
    includes = "\n    ".join(sdk_include_paths)

    mcu_flags = _get_mcu_flags(target_mcu)
    flags_str = " ".join(mcu_flags)

    sections = [
        f"cmake_minimum_required(VERSION 3.20)",
        f"project({project_name} C ASM)",
        "",
        f"set(CMAKE_C_STANDARD 11)",
        f"set(CMAKE_SYSTEM_NAME Generic)",
        f"set(CMAKE_SYSTEM_PROCESSOR arm)",
        f"set(CMAKE_C_COMPILER arm-none-eabi-gcc)",
        f"set(CMAKE_ASM_COMPILER arm-none-eabi-gcc)",
        "",
        f"set(MCU_FLAGS \"{flags_str}\")",
        f"set(CMAKE_C_FLAGS \"${{MCU_FLAGS}} -Wall -Wextra -O2 -fdata-sections -ffunction-sections\")",
        "",
        f"add_executable(${{PROJECT_NAME}}",
        f"    {sources}",
        f")",
        "",
        f"target_include_directories(${{PROJECT_NAME}} PRIVATE",
        f"    {includes}",
        f")",
    ]

    if linker_script:
        sections.extend([
            "",
            f"set(LINKER_SCRIPT {linker_script})",
            f"target_link_options(${{PROJECT_NAME}} PRIVATE",
            f"    -T${{LINKER_SCRIPT}}",
            f"    -Wl,--gc-sections",
            f"    -Wl,-Map=${{PROJECT_NAME}}.map",
            f"    --specs=nano.specs",
            f"    --specs=nosys.specs",
            f")",
        ])

    return "\n".join(sections) + "\n"


def generate_makefile(
    project_name: str,
    source_files: List[str],
    target_mcu: str,
    sdk_include_paths: List[str],
    linker_script: str = "",
) -> str:
    """Generate a Makefile for the embedded project."""
    mcu_flags = _get_mcu_flags(target_mcu)

    objects = " ".join(f.replace(".c", ".o") for f in source_files if f.endswith(".c"))
    includes = " ".join(f"-I{p}" for p in sdk_include_paths)
    mcu = " ".join(mcu_flags)

    lines = [
        f"PROJECT = {project_name}",
        f"CC = arm-none-eabi-gcc",
        f"OBJCOPY = arm-none-eabi-objcopy",
        f"SIZE = arm-none-eabi-size",
        f"",
        f"MCU_FLAGS = {mcu}",
        f"CFLAGS = $(MCU_FLAGS) -Wall -Wextra -O2 -std=c11 -fdata-sections -ffunction-sections",
        f"CFLAGS += {includes}",
        f"",
        f"SOURCES = {' '.join(source_files)}",
        f"OBJECTS = {objects}",
        f"",
    ]

    if linker_script:
        lines.extend([
            f"LDSCRIPT = {linker_script}",
            f"LDFLAGS = $(MCU_FLAGS) -T$(LDSCRIPT) -Wl,--gc-sections -Wl,-Map=$(PROJECT).map --specs=nano.specs --specs=nosys.specs",
            f"",
            f"all: $(PROJECT).bin",
            f"",
            f"$(PROJECT).elf: $(OBJECTS)",
            f"\t$(CC) $(LDFLAGS) $^ -o $@",
            f"\t$(SIZE) $@",
            f"",
            f"$(PROJECT).bin: $(PROJECT).elf",
            f"\t$(OBJCOPY) -O binary $< $@",
        ])
    else:
        lines.extend([
            f"all: $(OBJECTS)",
            f"\t@echo 'Compiled $(words $(OBJECTS)) object file(s)'",
        ])

    lines.extend([
        f"",
        f"%.o: %.c",
        f"\t$(CC) $(CFLAGS) -c $< -o $@",
        f"",
        f"clean:",
        f"\trm -f $(OBJECTS) $(PROJECT).elf $(PROJECT).bin $(PROJECT).map",
        f"",
        f".PHONY: all clean",
    ])

    return "\n".join(lines) + "\n"


def _get_mcu_flags(target_mcu: str) -> List[str]:
    mcu = target_mcu.upper()
    if mcu.startswith("STM32F4") or mcu.startswith("STM32G4"):
        return ["-mcpu=cortex-m4", "-mthumb", "-mfloat-abi=hard", "-mfpu=fpv4-sp-d16"]
    elif mcu.startswith("STM32F7") or mcu.startswith("STM32H7"):
        return ["-mcpu=cortex-m7", "-mthumb", "-mfloat-abi=hard", "-mfpu=fpv5-d16"]
    elif mcu.startswith("STM32L0") or mcu.startswith("STM32F0"):
        return ["-mcpu=cortex-m0plus", "-mthumb"]
    elif mcu.startswith("NRF52"):
        return ["-mcpu=cortex-m4", "-mthumb", "-mfloat-abi=hard", "-mfpu=fpv4-sp-d16"]
    elif mcu.startswith("ESP32"):
        return ["-mlongcalls"]
    return ["-mcpu=cortex-m4", "-mthumb"]

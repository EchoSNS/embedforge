"""STM32 Project Exporter — CMake + HAL config for STM32CubeIDE-compatible projects."""

from __future__ import annotations

from typing import Any, Dict

from plugins.base import BoardConfig, ProjectExporter


class STM32ProjectExporter(ProjectExporter):

    def get_build_system(self) -> str:
        return "cmake"

    def export(self, production_files, test_files, mock_files, board_config, output_dir):
        result = {}
        for name, content in production_files.items():
            result[f"src/{name}"] = content
        for name, content in test_files.items():
            result[f"tests/{name}"] = content
        for name, content in mock_files.items():
            result[f"tests/mocks/{name}"] = content
        result.update(self.get_project_files(board_config))
        return result

    def get_project_files(self, board_config: BoardConfig) -> Dict[str, str]:
        mcu = board_config.mcu.upper()
        family = board_config.mcu_family.upper().replace("STM32", "")
        freq = board_config.clock_hz

        files = {}

        files["CMakeLists.txt"] = f"""cmake_minimum_required(VERSION 3.20)

set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR arm)
set(CMAKE_C_COMPILER arm-none-eabi-gcc)
set(CMAKE_ASM_COMPILER arm-none-eabi-gcc)

project({board_config.name.replace("-", "_")} C ASM)
set(CMAKE_C_STANDARD 11)

# MCU flags
set(MCU_FLAGS "-mcpu=cortex-m4 -mthumb -mfloat-abi=hard -mfpu=fpv4-sp-d16")
set(CMAKE_C_FLAGS "${{CMAKE_C_FLAGS}} ${{MCU_FLAGS}} -Wall -fdata-sections -ffunction-sections")
set(CMAKE_EXE_LINKER_FLAGS "${{CMAKE_EXE_LINKER_FLAGS}} ${{MCU_FLAGS}} -Wl,--gc-sections -T${{CMAKE_SOURCE_DIR}}/linker_script.ld")

# HAL defines
add_definitions(-DUSE_HAL_DRIVER -D{mcu})

# Sources
file(GLOB_RECURSE SOURCES "src/*.c")

add_executable(${{PROJECT_NAME}}.elf ${{SOURCES}})

target_include_directories(${{PROJECT_NAME}}.elf PRIVATE
    src/Core/Inc
    src/
    $ENV{{STM32CUBE_{family[0]}x_PATH}}/Drivers/STM32{family}xx_HAL_Driver/Inc
    $ENV{{STM32CUBE_{family[0]}x_PATH}}/Drivers/CMSIS/Device/ST/STM32{family}xx/Include
    $ENV{{STM32CUBE_{family[0]}x_PATH}}/Drivers/CMSIS/Include
)

# Generate .bin and .hex
add_custom_command(TARGET ${{PROJECT_NAME}}.elf POST_BUILD
    COMMAND arm-none-eabi-objcopy -O binary ${{PROJECT_NAME}}.elf ${{PROJECT_NAME}}.bin
    COMMAND arm-none-eabi-objcopy -O ihex ${{PROJECT_NAME}}.elf ${{PROJECT_NAME}}.hex
    COMMAND arm-none-eabi-size ${{PROJECT_NAME}}.elf
)
"""

        files["stm32f4xx_hal_conf.h"] = f"""#ifndef __STM32{family}xx_HAL_CONF_H
#define __STM32{family}xx_HAL_CONF_H

#define HAL_MODULE_ENABLED
#define HAL_GPIO_MODULE_ENABLED
#define HAL_RCC_MODULE_ENABLED
#define HAL_CORTEX_MODULE_ENABLED
#define HAL_FLASH_MODULE_ENABLED
#define HAL_PWR_MODULE_ENABLED
#define HAL_TIM_MODULE_ENABLED
#define HAL_UART_MODULE_ENABLED
#define HAL_SPI_MODULE_ENABLED
#define HAL_I2C_MODULE_ENABLED
#define HAL_ADC_MODULE_ENABLED
#define HAL_DMA_MODULE_ENABLED
#define HAL_CAN_MODULE_ENABLED

#define HSE_VALUE {freq}U
#define LSE_VALUE 32768U

#include "stm32{family.lower()}xx_hal_def.h"

#endif
"""
        return files

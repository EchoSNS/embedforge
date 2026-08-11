"""
STM32 Board Templates — Nucleo-F446RE as the default example board.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from plugins.base import BoardConfig, BoardTemplate, PinMapping


class NucleoF446RE(BoardTemplate):
    """NUCLEO-F446RE board template (STM32F446RET6, 64-pin LQFP)."""

    def get_config(self) -> BoardConfig:
        return BoardConfig(
            name="NUCLEO-F446RE",
            mcu="STM32F446RET6",
            mcu_family="STM32F4",
            clock_hz=180_000_000,
            peripherals={
                "TIM1": {"type": "advanced", "channels": 4, "complementary": True},
                "TIM2": {"type": "general_purpose_32bit", "channels": 4},
                "TIM3": {"type": "general_purpose_16bit", "channels": 4},
                "TIM4": {"type": "general_purpose_16bit", "channels": 4},
                "ADC1": {"type": "adc", "channels": 16, "resolution_bits": 12},
                "USART1": {"type": "uart", "max_baud": 10_500_000},
                "USART2": {"type": "uart", "max_baud": 5_250_000, "note": "Connected to ST-LINK VCP"},
                "SPI1": {"type": "spi", "max_clock": 45_000_000},
                "I2C1": {"type": "i2c", "max_clock": 400_000},
                "CAN1": {"type": "can", "version": "2.0B"},
            },
        )

    def get_sdk_include_paths(self) -> List[str]:
        # Users must install STM32CubeF4 and set this env var or provide paths
        import os
        cube_path = os.getenv("STM32CUBE_F4_PATH", "")
        if cube_path:
            return [
                f"{cube_path}/Drivers/STM32F4xx_HAL_Driver/Inc",
                f"{cube_path}/Drivers/CMSIS/Device/ST/STM32F4xx/Include",
                f"{cube_path}/Drivers/CMSIS/Include",
            ]
        return []

    def get_template_files(self) -> Dict[str, str]:
        return {
            "main.c": _MAIN_TEMPLATE,
            "stm32f4xx_it.c": _IT_TEMPLATE,
            "stm32f4xx_hal_msp.c": _MSP_TEMPLATE,
            "stm32f4xx_hal_conf.h": "// HAL configuration — enable needed modules",
        }

    def get_linker_script(self) -> Optional[str]:
        return _LINKER_SCRIPT


_MAIN_TEMPLATE = """\
#include "main.h"
#include "stm32f4xx_hal.h"

void SystemClock_Config(void);
void Error_Handler(void);

int main(void) {
    HAL_Init();
    SystemClock_Config();

    // USER CODE — peripheral initialization goes here

    while (1) {
        // USER CODE — main loop
    }
}

void SystemClock_Config(void) {
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    __HAL_RCC_PWR_CLK_ENABLE();
    __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);

    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    RCC_OscInitStruct.HSEState = RCC_HSE_ON;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    RCC_OscInitStruct.PLL.PLLM = 8;
    RCC_OscInitStruct.PLL.PLLN = 360;
    RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV2;
    RCC_OscInitStruct.PLL.PLLQ = 7;

    if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK) {
        Error_Handler();
    }

    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK
                                | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV4;
    RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV2;

    if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_5) != HAL_OK) {
        Error_Handler();
    }
}

void Error_Handler(void) {
    __disable_irq();
    while (1) {}
}
"""

_IT_TEMPLATE = """\
#include "stm32f4xx_hal.h"

void NMI_Handler(void) {}
void HardFault_Handler(void) { while (1) {} }
void SysTick_Handler(void) { HAL_IncTick(); }
"""

_MSP_TEMPLATE = """\
#include "stm32f4xx_hal.h"

void HAL_MspInit(void) {
    __HAL_RCC_SYSCFG_CLK_ENABLE();
    __HAL_RCC_PWR_CLK_ENABLE();
}
"""

_LINKER_SCRIPT = """\
/* STM32F446RETx — 512KB Flash, 128KB RAM */
MEMORY {
    FLASH (rx) : ORIGIN = 0x08000000, LENGTH = 512K
    RAM (xrw)  : ORIGIN = 0x20000000, LENGTH = 128K
}

ENTRY(Reset_Handler)

SECTIONS {
    .text : { *(.isr_vector) *(.text*) *(.rodata*) } > FLASH
    .data : { *(.data*) } > RAM AT > FLASH
    .bss  : { *(.bss*) *(COMMON) } > RAM
}
"""

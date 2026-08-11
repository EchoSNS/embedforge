"""
STM32 HAL Architecture Rules — coding conventions for STM32 HAL projects.
"""

from __future__ import annotations

import re
from typing import Dict, List

from plugins.base import ArchitectureRulePack


class STM32ArchitectureRules(ArchitectureRulePack):
    """Architecture rules for STM32 HAL-based projects."""

    def get_rules_text(self) -> str:
        return _RULES_TEXT

    def get_init_pattern(self, driver_name: str) -> str:
        return _INIT_PATTERNS.get(driver_name, _DEFAULT_INIT_PATTERN)

    def get_naming_conventions(self) -> Dict[str, str]:
        return {
            "handle_prefix": "h (e.g. htim1, huart2, hadc1)",
            "init_function": "<module>_Init() in main.c or dedicated init file",
            "callback_naming": "HAL_<Peripheral>_<Event>Callback()",
            "config_struct": "<Peripheral>_HandleTypeDef + <Peripheral>_InitTypeDef",
            "file_naming": "main.c, stm32f4xx_hal_conf.h, stm32f4xx_it.c",
            "isr_naming": "<Peripheral>_IRQHandler (e.g. TIM1_UP_TIM10_IRQHandler)",
            "clock_enable": "__HAL_RCC_<PERIPH>_CLK_ENABLE() in HAL_<Periph>_MspInit()",
            "gpio_init_location": "HAL_<Periph>_MspInit() — NOT in main()",
        }

    def validate_code(self, code: str) -> List[str]:
        violations: List[str] = []

        # Check: clock must be enabled before peripheral use
        if "HAL_TIM_PWM_Start" in code and "__HAL_RCC_TIM" not in code:
            if "MspInit" not in code:
                violations.append(
                    "Timer clock not enabled. Add __HAL_RCC_TIMx_CLK_ENABLE() "
                    "in HAL_TIM_Base_MspInit() or before HAL_TIM_PWM_Init()."
                )

        # Check: GPIO init should be in MspInit, not main
        if re.search(r"int\s+main\s*\(", code) and "HAL_GPIO_Init" in code:
            if "MspInit" not in code:
                violations.append(
                    "GPIO init should be in HAL_<Periph>_MspInit(), not directly in main()."
                )

        # Check: handle must be declared
        if "htim" in code and "TIM_HandleTypeDef" not in code:
            violations.append("Timer handle 'htim' used but TIM_HandleTypeDef not declared.")

        return violations


_RULES_TEXT = """STM32 HAL Architecture Rules:

1. PERIPHERAL INITIALIZATION ORDER:
   a. Enable peripheral clock: __HAL_RCC_<PERIPH>_CLK_ENABLE()
   b. Configure GPIO pins in HAL_<Periph>_MspInit()
   c. Initialize peripheral: HAL_<Periph>_Init(&handle)
   d. Configure channels/features
   e. Start peripheral: HAL_<Periph>_Start(&handle)

2. HANDLE PATTERN:
   - Every peripheral has a handle: <Periph>_HandleTypeDef h<periph>
   - Handle contains Init struct with configuration
   - Handle is passed to ALL HAL functions for that peripheral

3. MSP (MCU Support Package) PATTERN:
   - HAL_<Periph>_MspInit() is called automatically by HAL_<Periph>_Init()
   - GPIO pin config and clock enable go in MspInit
   - HAL_<Periph>_MspDeInit() for teardown

4. INTERRUPT PATTERN:
   - Enable NVIC: HAL_NVIC_SetPriority() + HAL_NVIC_EnableIRQ()
   - ISR calls HAL_<Periph>_IRQHandler(&handle)
   - User code goes in HAL_<Periph>_<Event>Callback()
   - NEVER put application logic directly in the IRQHandler

5. NAMING CONVENTIONS:
   - Handles: htim1, huart2, hadc1, hspi1
   - Files: main.c, stm32f4xx_it.c (ISR vectors), stm32f4xx_hal_msp.c
   - Functions: MX_<Periph>_Init(), SystemClock_Config()

6. ERROR HANDLING:
   - Check HAL_StatusTypeDef return values (HAL_OK, HAL_ERROR, HAL_BUSY, HAL_TIMEOUT)
   - Implement Error_Handler() for unrecoverable errors
"""

_DEFAULT_INIT_PATTERN = """
// 1. Declare handle
<Periph>_HandleTypeDef h<periph>;

// 2. Configure init struct
h<periph>.Instance = <INSTANCE>;
h<periph>.Init.<field> = <value>;

// 3. Initialize
if (HAL_<Periph>_Init(&h<periph>) != HAL_OK) {
    Error_Handler();
}
"""

_INIT_PATTERNS: Dict[str, str] = {
    "HAL_TIM_PWM": """
TIM_HandleTypeDef htim1;
TIM_OC_InitTypeDef sConfigOC = {0};

htim1.Instance = TIM1;
htim1.Init.Prescaler = prescaler;
htim1.Init.CounterMode = TIM_COUNTERMODE_UP;
htim1.Init.Period = period;
htim1.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;

if (HAL_TIM_PWM_Init(&htim1) != HAL_OK) {
    Error_Handler();
}

sConfigOC.OCMode = TIM_OCMODE_PWM1;
sConfigOC.Pulse = duty;
sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;

if (HAL_TIM_PWM_ConfigChannel(&htim1, &sConfigOC, TIM_CHANNEL_1) != HAL_OK) {
    Error_Handler();
}

HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);
""",
    "HAL_GPIO": """
GPIO_InitTypeDef GPIO_InitStruct = {0};

__HAL_RCC_GPIOA_CLK_ENABLE();

GPIO_InitStruct.Pin = GPIO_PIN_5;
GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
GPIO_InitStruct.Pull = GPIO_NOPULL;
GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;

HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);
""",
    "HAL_UART": """
UART_HandleTypeDef huart2;

huart2.Instance = USART2;
huart2.Init.BaudRate = 115200;
huart2.Init.WordLength = UART_WORDLENGTH_8B;
huart2.Init.StopBits = UART_STOPBITS_1;
huart2.Init.Parity = UART_PARITY_NONE;
huart2.Init.Mode = UART_MODE_TX_RX;
huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;

if (HAL_UART_Init(&huart2) != HAL_OK) {
    Error_Handler();
}
""",
}

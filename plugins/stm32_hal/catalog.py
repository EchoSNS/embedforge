"""
STM32 HAL Driver Catalog — registry of available HAL drivers.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from plugins.base import ApiLayer, DriverCatalog, DriverInfo


_DRIVERS: List[DriverInfo] = [
    # --- GPIO ---
    DriverInfo(
        name="HAL_GPIO",
        api_layer=ApiLayer.HIGH_LEVEL,
        peripheral="GPIO",
        description="GPIO init, read, write, toggle, EXTI config",
        when_to_use="Any digital I/O, LED control, button input",
    ),
    # --- TIM / PWM ---
    DriverInfo(
        name="HAL_TIM_PWM",
        api_layer=ApiLayer.HIGH_LEVEL,
        peripheral="PWM",
        description="Timer PWM generation with HAL",
        handles_internally=("output_compare", "prescaler_calc", "auto_reload"),
        when_to_use="Basic PWM output, LED dimming, servo control",
        when_not_to_use="Advanced motor control with complementary outputs — use HAL_TIM_PWM_N",
        companion_drivers=("HAL_RCC",),
    ),
    DriverInfo(
        name="HAL_TIM_PWM_N",
        api_layer=ApiLayer.HIGH_LEVEL,
        peripheral="PWM",
        description="Complementary PWM with dead-time (TIM1/TIM8 advanced timers)",
        handles_internally=("complementary_output", "dead_time_generator", "break_input"),
        when_to_use="3-phase motor control, H-bridge, inverter with dead-time",
        companion_drivers=("HAL_RCC",),
    ),
    DriverInfo(
        name="HAL_TIM_Base",
        api_layer=ApiLayer.MID_LEVEL,
        peripheral="TIMER",
        description="Timer base (timebase generation, delays, periodic interrupts)",
        when_to_use="Periodic interrupts, timebase, input capture trigger",
    ),
    DriverInfo(
        name="HAL_TIM_IC",
        api_layer=ApiLayer.HIGH_LEVEL,
        peripheral="TIMER",
        description="Timer input capture (frequency/duty measurement)",
        when_to_use="Frequency measurement, encoder interface, pulse width capture",
    ),
    # --- ADC ---
    DriverInfo(
        name="HAL_ADC",
        api_layer=ApiLayer.HIGH_LEVEL,
        peripheral="ADC",
        description="ADC single/scan conversion with polling, interrupt, or DMA",
        handles_internally=("channel_config", "calibration", "sequence"),
        when_to_use="Analog voltage measurement, sensor reading",
        companion_drivers=("HAL_RCC", "HAL_DMA"),
    ),
    # --- UART ---
    DriverInfo(
        name="HAL_UART",
        api_layer=ApiLayer.HIGH_LEVEL,
        peripheral="UART",
        description="UART transmit/receive with polling, IT, or DMA",
        handles_internally=("baud_config", "parity", "flow_control"),
        when_to_use="Serial communication, debug console, sensor UART",
        companion_drivers=("HAL_RCC",),
    ),
    # --- SPI ---
    DriverInfo(
        name="HAL_SPI",
        api_layer=ApiLayer.HIGH_LEVEL,
        peripheral="SPI",
        description="SPI master/slave with polling, IT, or DMA",
        handles_internally=("clock_polarity", "clock_phase", "nss_management"),
        when_to_use="SPI flash, display, sensor communication",
        companion_drivers=("HAL_RCC", "HAL_GPIO"),
    ),
    # --- I2C ---
    DriverInfo(
        name="HAL_I2C",
        api_layer=ApiLayer.HIGH_LEVEL,
        peripheral="I2C",
        description="I2C master/slave communication",
        handles_internally=("addressing", "clock_stretching", "error_recovery"),
        when_to_use="I2C sensors, EEPROM, display controllers",
        companion_drivers=("HAL_RCC",),
    ),
    # --- DMA ---
    DriverInfo(
        name="HAL_DMA",
        api_layer=ApiLayer.SUPPORT,
        peripheral="DMA",
        description="DMA channel configuration for peripheral-to-memory transfers",
        when_to_use="High-throughput data transfer without CPU involvement",
    ),
    # --- RCC (Clock) ---
    DriverInfo(
        name="HAL_RCC",
        api_layer=ApiLayer.SUPPORT,
        peripheral="CLOCK",
        description="Reset and Clock Control — enable peripheral clocks",
        when_to_use="Always required — enables clocks for all peripherals",
    ),
    # --- CAN ---
    DriverInfo(
        name="HAL_CAN",
        api_layer=ApiLayer.HIGH_LEVEL,
        peripheral="CAN",
        description="CAN bus communication (Classic CAN 2.0)",
        handles_internally=("filter_config", "mailbox_management", "error_handling"),
        when_to_use="Vehicle/industrial CAN bus communication",
        companion_drivers=("HAL_RCC",),
    ),
]


class STM32DriverCatalog(DriverCatalog):
    """STM32 HAL driver catalog implementation."""

    def __init__(self) -> None:
        self._by_name: Dict[str, DriverInfo] = {d.name: d for d in _DRIVERS}
        self._by_peripheral: Dict[str, List[DriverInfo]] = {}
        for d in _DRIVERS:
            self._by_peripheral.setdefault(d.peripheral, []).append(d)

    def list_peripherals(self) -> List[str]:
        return sorted(self._by_peripheral.keys())

    def list_drivers(self, peripheral: str) -> List[DriverInfo]:
        return self._by_peripheral.get(peripheral.upper(), [])

    def get_driver(self, name: str) -> Optional[DriverInfo]:
        return self._by_name.get(name)

    def recommend_driver(self, peripheral: str, requirements: Dict[str, Any]) -> Optional[DriverInfo]:
        candidates = self.list_drivers(peripheral)
        if not candidates:
            return None

        # Simple heuristic: prefer HIGH_LEVEL for complex, MID for simple
        channel_count = requirements.get("channel_count", 1)
        needs_complementary = requirements.get("needs_complementary", False)

        if needs_complementary:
            for d in candidates:
                if "complementary" in " ".join(d.handles_internally):
                    return d

        # Default to first high-level driver
        for d in candidates:
            if d.api_layer == ApiLayer.HIGH_LEVEL:
                return d

        return candidates[0]

    def get_driver_functions(self, driver_name: str) -> List[Dict[str, str]]:
        return _DRIVER_FUNCTIONS.get(driver_name, [])

    def get_driver_types(self, driver_name: str) -> List[Dict[str, str]]:
        return _DRIVER_TYPES.get(driver_name, [])


# Minimal function/type registry for demonstration
_DRIVER_FUNCTIONS: Dict[str, List[Dict[str, str]]] = {
    "HAL_GPIO": [
        {"name": "HAL_GPIO_Init", "signature": "void HAL_GPIO_Init(GPIO_TypeDef *GPIOx, GPIO_InitTypeDef *GPIO_Init)"},
        {"name": "HAL_GPIO_WritePin", "signature": "void HAL_GPIO_WritePin(GPIO_TypeDef *GPIOx, uint16_t GPIO_Pin, GPIO_PinState PinState)"},
        {"name": "HAL_GPIO_ReadPin", "signature": "GPIO_PinState HAL_GPIO_ReadPin(GPIO_TypeDef *GPIOx, uint16_t GPIO_Pin)"},
        {"name": "HAL_GPIO_TogglePin", "signature": "void HAL_GPIO_TogglePin(GPIO_TypeDef *GPIOx, uint16_t GPIO_Pin)"},
    ],
    "HAL_TIM_PWM": [
        {"name": "HAL_TIM_PWM_Init", "signature": "HAL_StatusTypeDef HAL_TIM_PWM_Init(TIM_HandleTypeDef *htim)"},
        {"name": "HAL_TIM_PWM_Start", "signature": "HAL_StatusTypeDef HAL_TIM_PWM_Start(TIM_HandleTypeDef *htim, uint32_t Channel)"},
        {"name": "HAL_TIM_PWM_Stop", "signature": "HAL_StatusTypeDef HAL_TIM_PWM_Stop(TIM_HandleTypeDef *htim, uint32_t Channel)"},
        {"name": "HAL_TIM_PWM_ConfigChannel", "signature": "HAL_StatusTypeDef HAL_TIM_PWM_ConfigChannel(TIM_HandleTypeDef *htim, TIM_OC_InitTypeDef *sConfig, uint32_t Channel)"},
        {"name": "__HAL_TIM_SET_COMPARE", "signature": "__HAL_TIM_SET_COMPARE(htim, Channel, Compare)"},
    ],
    "HAL_TIM_PWM_N": [
        {"name": "HAL_TIMEx_PWMN_Start", "signature": "HAL_StatusTypeDef HAL_TIMEx_PWMN_Start(TIM_HandleTypeDef *htim, uint32_t Channel)"},
        {"name": "HAL_TIMEx_ConfigBreakDeadTime", "signature": "HAL_StatusTypeDef HAL_TIMEx_ConfigBreakDeadTime(TIM_HandleTypeDef *htim, TIM_BreakDeadTimeConfigTypeDef *sBreakDeadTimeConfig)"},
    ],
    "HAL_ADC": [
        {"name": "HAL_ADC_Init", "signature": "HAL_StatusTypeDef HAL_ADC_Init(ADC_HandleTypeDef *hadc)"},
        {"name": "HAL_ADC_Start", "signature": "HAL_StatusTypeDef HAL_ADC_Start(ADC_HandleTypeDef *hadc)"},
        {"name": "HAL_ADC_PollForConversion", "signature": "HAL_StatusTypeDef HAL_ADC_PollForConversion(ADC_HandleTypeDef *hadc, uint32_t Timeout)"},
        {"name": "HAL_ADC_GetValue", "signature": "uint32_t HAL_ADC_GetValue(ADC_HandleTypeDef *hadc)"},
    ],
    "HAL_UART": [
        {"name": "HAL_UART_Init", "signature": "HAL_StatusTypeDef HAL_UART_Init(UART_HandleTypeDef *huart)"},
        {"name": "HAL_UART_Transmit", "signature": "HAL_StatusTypeDef HAL_UART_Transmit(UART_HandleTypeDef *huart, uint8_t *pData, uint16_t Size, uint32_t Timeout)"},
        {"name": "HAL_UART_Receive", "signature": "HAL_StatusTypeDef HAL_UART_Receive(UART_HandleTypeDef *huart, uint8_t *pData, uint16_t Size, uint32_t Timeout)"},
        {"name": "HAL_UART_Transmit_IT", "signature": "HAL_StatusTypeDef HAL_UART_Transmit_IT(UART_HandleTypeDef *huart, uint8_t *pData, uint16_t Size)"},
    ],
}

_DRIVER_TYPES: Dict[str, List[Dict[str, str]]] = {
    "HAL_GPIO": [
        {"name": "GPIO_InitTypeDef", "kind": "struct"},
        {"name": "GPIO_PinState", "kind": "enum"},
    ],
    "HAL_TIM_PWM": [
        {"name": "TIM_HandleTypeDef", "kind": "struct"},
        {"name": "TIM_OC_InitTypeDef", "kind": "struct"},
    ],
    "HAL_ADC": [
        {"name": "ADC_HandleTypeDef", "kind": "struct"},
        {"name": "ADC_ChannelConfTypeDef", "kind": "struct"},
    ],
    "HAL_UART": [
        {"name": "UART_HandleTypeDef", "kind": "struct"},
        {"name": "UART_InitTypeDef", "kind": "struct"},
    ],
}

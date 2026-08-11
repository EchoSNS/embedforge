"""
STM32 Pin Capability Provider — pin maps for STM32F446 (Nucleo-64).
"""

from __future__ import annotations

from typing import Dict, List

from plugins.base import PinCapabilityProvider, PinMapping


# Subset of STM32F446RE LQFP64 pin alternate functions
_PIN_DATABASE: List[PinMapping] = [
    # GPIO (usable as general I/O)
    PinMapping(symbol="PA5", port="A", pin=5, peripheral="GPIO", function="LED (LD2)"),
    PinMapping(symbol="PC13", port="C", pin=13, peripheral="GPIO", function="USER_BUTTON (B1)"),
    # TIM1 — Advanced timer (complementary PWM)
    PinMapping(symbol="PA8", port="A", pin=8, peripheral="PWM", function="TIM1_CH1", alternate_function=1),
    PinMapping(symbol="PA9", port="A", pin=9, peripheral="PWM", function="TIM1_CH2", alternate_function=1),
    PinMapping(symbol="PA10", port="A", pin=10, peripheral="PWM", function="TIM1_CH3", alternate_function=1),
    PinMapping(symbol="PB13", port="B", pin=13, peripheral="PWM", function="TIM1_CH1N", alternate_function=1, is_complementary=True),
    PinMapping(symbol="PB14", port="B", pin=14, peripheral="PWM", function="TIM1_CH2N", alternate_function=1, is_complementary=True),
    PinMapping(symbol="PB15", port="B", pin=15, peripheral="PWM", function="TIM1_CH3N", alternate_function=1, is_complementary=True),
    # TIM2 — General purpose timer
    PinMapping(symbol="PA0", port="A", pin=0, peripheral="PWM", function="TIM2_CH1", alternate_function=1),
    PinMapping(symbol="PA1", port="A", pin=1, peripheral="PWM", function="TIM2_CH2", alternate_function=1),
    PinMapping(symbol="PB10", port="B", pin=10, peripheral="PWM", function="TIM2_CH3", alternate_function=1),
    PinMapping(symbol="PB11", port="B", pin=11, peripheral="PWM", function="TIM2_CH4", alternate_function=1),
    # TIM3
    PinMapping(symbol="PA6", port="A", pin=6, peripheral="PWM", function="TIM3_CH1", alternate_function=2),
    PinMapping(symbol="PA7", port="A", pin=7, peripheral="PWM", function="TIM3_CH2", alternate_function=2),
    PinMapping(symbol="PB0", port="B", pin=0, peripheral="PWM", function="TIM3_CH3", alternate_function=2),
    PinMapping(symbol="PB1", port="B", pin=1, peripheral="PWM", function="TIM3_CH4", alternate_function=2),
    # ADC1
    PinMapping(symbol="PA0", port="A", pin=0, peripheral="ADC", function="ADC1_IN0"),
    PinMapping(symbol="PA1", port="A", pin=1, peripheral="ADC", function="ADC1_IN1"),
    PinMapping(symbol="PA2", port="A", pin=2, peripheral="ADC", function="ADC1_IN2"),
    PinMapping(symbol="PA3", port="A", pin=3, peripheral="ADC", function="ADC1_IN3"),
    PinMapping(symbol="PA4", port="A", pin=4, peripheral="ADC", function="ADC1_IN4"),
    PinMapping(symbol="PC0", port="C", pin=0, peripheral="ADC", function="ADC1_IN10"),
    PinMapping(symbol="PC1", port="C", pin=1, peripheral="ADC", function="ADC1_IN11"),
    # UART2 (connected to ST-LINK VCP)
    PinMapping(symbol="PA2", port="A", pin=2, peripheral="UART", function="USART2_TX", alternate_function=7),
    PinMapping(symbol="PA3", port="A", pin=3, peripheral="UART", function="USART2_RX", alternate_function=7),
    # UART1
    PinMapping(symbol="PA9", port="A", pin=9, peripheral="UART", function="USART1_TX", alternate_function=7),
    PinMapping(symbol="PA10", port="A", pin=10, peripheral="UART", function="USART1_RX", alternate_function=7),
    # SPI1
    PinMapping(symbol="PA5", port="A", pin=5, peripheral="SPI", function="SPI1_SCK", alternate_function=5),
    PinMapping(symbol="PA6", port="A", pin=6, peripheral="SPI", function="SPI1_MISO", alternate_function=5),
    PinMapping(symbol="PA7", port="A", pin=7, peripheral="SPI", function="SPI1_MOSI", alternate_function=5),
    # I2C1
    PinMapping(symbol="PB8", port="B", pin=8, peripheral="I2C", function="I2C1_SCL", alternate_function=4),
    PinMapping(symbol="PB9", port="B", pin=9, peripheral="I2C", function="I2C1_SDA", alternate_function=4),
]

_VALID_SYMBOLS = frozenset(p.symbol for p in _PIN_DATABASE)


class STM32PinProvider(PinCapabilityProvider):
    """Pin capability provider for STM32F446RE (LQFP64 package)."""

    def get_available_pins(self, peripheral: str, function: str = "") -> List[PinMapping]:
        peripheral_upper = peripheral.upper()
        results = [p for p in _PIN_DATABASE if p.peripheral == peripheral_upper]
        if function:
            results = [p for p in results if function.upper() in p.function.upper()]
        return results

    def validate_pin(self, symbol: str) -> bool:
        return symbol in _VALID_SYMBOLS

    def validate_assignment(self, assignments: Dict[str, str]) -> List[str]:
        errors: List[str] = []
        used_pins: Dict[str, str] = {}

        for func_name, pin_symbol in assignments.items():
            if pin_symbol not in _VALID_SYMBOLS:
                errors.append(f"Invalid pin '{pin_symbol}' for function '{func_name}'")
                continue

            if pin_symbol in used_pins:
                errors.append(
                    f"Pin conflict: '{pin_symbol}' assigned to both "
                    f"'{used_pins[pin_symbol]}' and '{func_name}'"
                )
            else:
                used_pins[pin_symbol] = func_name

        return errors

    def get_pin_patterns(self) -> Dict[str, str]:
        return {
            "gpio": r"P[A-H]\d{1,2}",
            "tim_channel": r"TIM\d+_CH\d+N?",
            "adc_channel": r"ADC\d+_IN\d+",
            "uart_pin": r"USART\d+_(?:TX|RX|CK|CTS|RTS)",
            "spi_pin": r"SPI\d+_(?:SCK|MISO|MOSI|NSS)",
            "i2c_pin": r"I2C\d+_(?:SCL|SDA)",
        }

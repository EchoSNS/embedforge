"""ESP32 board templates."""

from __future__ import annotations

import os
from typing import Dict, List, Optional

from plugins.base import BoardConfig, BoardTemplate


class ESP32DevKitC(BoardTemplate):
    """ESP32-DevKitC development board (ESP32-WROOM-32)."""

    def get_config(self) -> BoardConfig:
        return BoardConfig(
            name="ESP32-DevKitC",
            mcu="ESP32",
            mcu_family="ESP32",
            clock_hz=240_000_000,
            peripherals={
                "UART0": {"type": "uart", "note": "Default console/programming"},
                "UART1": {"type": "uart"},
                "UART2": {"type": "uart"},
                "SPI2": {"type": "spi", "note": "HSPI"},
                "SPI3": {"type": "spi", "note": "VSPI"},
                "I2C0": {"type": "i2c"},
                "I2C1": {"type": "i2c"},
                "LEDC": {"type": "pwm", "channels": 16},
                "MCPWM0": {"type": "pwm", "channels": 6, "note": "Motor control"},
                "ADC1": {"type": "adc", "channels": 8, "resolution_bits": 12},
                "ADC2": {"type": "adc", "channels": 10, "note": "Cannot use with WiFi"},
                "DAC": {"type": "dac", "channels": 2},
                "TWAI": {"type": "can"},
            },
        )

    def get_sdk_include_paths(self) -> List[str]:
        idf = os.getenv("IDF_PATH", "")
        if idf:
            return [
                f"{idf}/components/driver/include",
                f"{idf}/components/esp_adc/include",
                f"{idf}/components/hal/include",
            ]
        return []

    def get_template_files(self) -> Dict[str, str]:
        return {}

    def get_linker_script(self) -> Optional[str]:
        return None

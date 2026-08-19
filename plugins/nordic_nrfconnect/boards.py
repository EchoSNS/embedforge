"""Nordic board templates."""

from __future__ import annotations

import os
from typing import Dict, List, Optional

from plugins.base import BoardConfig, BoardTemplate


class NRF52840DK(BoardTemplate):
    """nRF52840 Development Kit (PCA10056)."""

    def get_config(self) -> BoardConfig:
        return BoardConfig(
            name="nRF52840-DK",
            mcu="nRF52840",
            mcu_family="nRF52",
            clock_hz=64_000_000,
            peripherals={
                "UARTE0": {"type": "uart", "note": "Default UART via J-Link VCP"},
                "UARTE1": {"type": "uart"},
                "SPIM0": {"type": "spi"},
                "TWIM0": {"type": "i2c"},
                "PWM0": {"type": "pwm", "channels": 4},
                "SAADC": {"type": "adc", "channels": 8, "resolution_bits": 14},
                "TIMER0": {"type": "timer", "note": "Reserved by SoftDevice if BLE used"},
            },
        )

    def get_sdk_include_paths(self) -> List[str]:
        sdk = os.getenv("NRF_SDK_PATH", "")
        if sdk:
            return [
                f"{sdk}/modules/hal/nordic/nrfx",
                f"{sdk}/modules/hal/nordic/nrfx/drivers/include",
                f"{sdk}/modules/hal/cmsis/CMSIS/Core/Include",
            ]
        return []

    def get_template_files(self) -> Dict[str, str]:
        return {}

    def get_linker_script(self) -> Optional[str]:
        return None

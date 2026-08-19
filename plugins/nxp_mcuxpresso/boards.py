"""NXP board templates."""

from __future__ import annotations

import os
from typing import Dict, List, Optional

from plugins.base import BoardConfig, BoardTemplate


class LPCXpresso55S69(BoardTemplate):
    """LPCXpresso55S69 development board (LPC55S69, dual Cortex-M33)."""

    def get_config(self) -> BoardConfig:
        return BoardConfig(
            name="LPCXpresso55S69",
            mcu="LPC55S69JBD100",
            mcu_family="LPC55S6x",
            clock_hz=150_000_000,
            peripherals={
                "FLEXCOMM0": {"type": "uart", "note": "Default debug UART"},
                "FLEXCOMM4": {"type": "spi"},
                "FLEXCOMM5": {"type": "i2c"},
                "CTIMER0": {"type": "timer", "channels": 4},
                "ADC0": {"type": "adc", "channels": 16, "resolution_bits": 16},
            },
        )

    def get_sdk_include_paths(self) -> List[str]:
        sdk = os.getenv("MCUXPRESSO_SDK_PATH", "")
        if sdk:
            return [
                f"{sdk}/devices/LPC55S69/drivers",
                f"{sdk}/devices/LPC55S69",
                f"{sdk}/CMSIS/Include",
            ]
        return []

    def get_template_files(self) -> Dict[str, str]:
        return {}

    def get_linker_script(self) -> Optional[str]:
        return None

"""AURIX board templates."""
from __future__ import annotations
import os
from typing import Dict, List, Optional
from plugins.base import BoardConfig, BoardTemplate

class TC4D7LiteKit(BoardTemplate):
    """AURIX TC4D7 Lite Kit (TC4D7 TriCore, 300MHz, automotive-grade)."""
    def get_config(self) -> BoardConfig:
        return BoardConfig(
            name="AURIX-TC4D7-LiteKit",
            mcu="TC4D7",
            mcu_family="TC4xx",
            clock_hz=300_000_000,
            peripherals={
                "ASCLIN0": {"type": "uart", "note": "Debug UART via USB"},
                "ASCLIN1": {"type": "uart"},
                "QSPI0": {"type": "spi"},
                "I2C0": {"type": "i2c"},
                "GTM_TOM0": {"type": "pwm", "channels": 16},
                "VADC_G0": {"type": "adc", "channels": 8, "resolution_bits": 12},
                "MULTICAN0": {"type": "can", "version": "FD", "nodes": 4},
                "GETH": {"type": "ethernet"},
                "STM0": {"type": "timer", "note": "System Timer"},
            },
        )

    def get_sdk_include_paths(self) -> List[str]:
        sdk = os.getenv("AURIX_SDK_PATH", "")
        if sdk:
            return [
                f"{sdk}/Libraries/iLLD/TC4D/Tricore",
                f"{sdk}/Libraries/Infra/Platform",
                f"{sdk}/Libraries/Service/CpuGeneric",
            ]
        return []

    def get_template_files(self) -> Dict[str, str]:
        return {}

    def get_linker_script(self) -> Optional[str]:
        return None

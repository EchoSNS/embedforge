"""Renesas board templates."""
from __future__ import annotations
import os
from typing import Dict, List, Optional
from plugins.base import BoardConfig, BoardTemplate

class EKRA6M5(BoardTemplate):
    """EK-RA6M5 evaluation kit (R7FA6M5BH3CFC, Cortex-M33)."""
    def get_config(self) -> BoardConfig:
        return BoardConfig(name="EK-RA6M5", mcu="R7FA6M5BH3CFC", mcu_family="RA6M5",
                           clock_hz=200_000_000,
                           peripherals={
                               "SCI0": {"type": "uart", "note": "Debug UART via J-Link VCP"},
                               "SCI9": {"type": "uart"},
                               "SPI0": {"type": "spi"}, "IIC0": {"type": "i2c"},
                               "GPT0": {"type": "pwm", "channels": 2},
                               "ADC0": {"type": "adc", "channels": 16, "resolution_bits": 12},
                               "CAN0": {"type": "can"},
                           })
    def get_sdk_include_paths(self) -> List[str]:
        fsp = os.getenv("FSP_PATH", "")
        return [f"{fsp}/ra/fsp/inc", f"{fsp}/ra/fsp/inc/api"] if fsp else []
    def get_template_files(self) -> Dict[str, str]:
        return {}
    def get_linker_script(self) -> Optional[str]:
        return None

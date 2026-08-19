"""Microchip board templates."""
from __future__ import annotations
import os
from typing import Dict, List, Optional
from plugins.base import BoardConfig, BoardTemplate

class SAME54Xplained(BoardTemplate):
    """SAM E54 Xplained Pro (ATSAME54P20A, Cortex-M4F)."""
    def get_config(self) -> BoardConfig:
        return BoardConfig(name="SAM-E54-Xplained-Pro", mcu="ATSAME54P20A",
                           mcu_family="SAME54", clock_hz=120_000_000,
                           peripherals={
                               "SERCOM2": {"type": "uart", "note": "EDBG Virtual COM"},
                               "SERCOM4": {"type": "spi"}, "SERCOM7": {"type": "i2c"},
                               "TCC0": {"type": "pwm", "channels": 6},
                               "ADC0": {"type": "adc", "channels": 16, "resolution_bits": 12},
                               "CAN0": {"type": "can", "version": "FD"},
                           })
    def get_sdk_include_paths(self) -> List[str]:
        h3 = os.getenv("HARMONY3_PATH", "")
        return [f"{h3}/csp/peripheral", f"{h3}/csp/include"] if h3 else []
    def get_template_files(self) -> Dict[str, str]:
        return {}
    def get_linker_script(self) -> Optional[str]:
        return None

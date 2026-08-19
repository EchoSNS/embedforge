"""Infineon board templates."""
from __future__ import annotations
import os
from typing import Dict, List, Optional
from plugins.base import BoardConfig, BoardTemplate

class CY8CProto062(BoardTemplate):
    """CY8CPROTO-062-4343W prototyping kit (PSoC 62 + CYW4343W WiFi/BT)."""
    def get_config(self) -> BoardConfig:
        return BoardConfig(name="CY8CPROTO-062-4343W", mcu="CY8C6247BZI-D54",
                           mcu_family="PSoC 62", clock_hz=150_000_000,
                           peripherals={
                               "SCB0": {"type": "uart", "note": "KitProg3 debug UART"},
                               "SCB1": {"type": "spi"}, "SCB3": {"type": "i2c"},
                               "TCPWM0": {"type": "pwm", "channels": 8},
                               "SAR": {"type": "adc", "channels": 16, "resolution_bits": 12},
                           })
    def get_sdk_include_paths(self) -> List[str]:
        mtb = os.getenv("MTB_PATH", "")
        return [f"{mtb}/pdl/drivers/include", f"{mtb}/hal/include"] if mtb else []
    def get_template_files(self) -> Dict[str, str]:
        return {}
    def get_linker_script(self) -> Optional[str]:
        return None

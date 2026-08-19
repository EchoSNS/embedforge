"""TI board templates."""
from __future__ import annotations
import os
from typing import Dict, List, Optional
from plugins.base import BoardConfig, BoardTemplate

class CC26X2RLaunchpad(BoardTemplate):
    """CC26X2R1 LaunchPad (CC2652R, Cortex-M4F, BLE 5 + IEEE 802.15.4)."""
    def get_config(self) -> BoardConfig:
        return BoardConfig(name="CC26X2R1-LAUNCHXL", mcu="CC2652R1FRGZ",
                           mcu_family="CC26x2", clock_hz=48_000_000,
                           peripherals={
                               "UART0": {"type": "uart", "note": "XDS110 debug UART"},
                               "SPI0": {"type": "spi"}, "I2C0": {"type": "i2c"},
                               "GPTimer0": {"type": "pwm", "channels": 2},
                               "ADC": {"type": "adc", "channels": 8, "resolution_bits": 12},
                           })
    def get_sdk_include_paths(self) -> List[str]:
        sdk = os.getenv("SIMPLELINK_SDK_PATH", "")
        return [f"{sdk}/source", f"{sdk}/source/ti/drivers"] if sdk else []
    def get_template_files(self) -> Dict[str, str]:
        return {}
    def get_linker_script(self) -> Optional[str]:
        return None

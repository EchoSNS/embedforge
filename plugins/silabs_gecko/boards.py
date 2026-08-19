"""Silicon Labs board templates."""
from __future__ import annotations
import os
from typing import Dict, List, Optional
from plugins.base import BoardConfig, BoardTemplate

class BRD4187C(BoardTemplate):
    """EFR32xG24 Radio Board (BRD4187C, Cortex-M33, BLE/Zigbee/Thread)."""
    def get_config(self) -> BoardConfig:
        return BoardConfig(name="BRD4187C", mcu="EFR32MG24B210F1536IM48",
                           mcu_family="EFR32MG24", clock_hz=78_000_000,
                           peripherals={
                               "USART0": {"type": "uart"},
                               "EUSART1": {"type": "uart", "note": "Enhanced USART"},
                               "SPI": {"type": "spi"}, "I2C0": {"type": "i2c"},
                               "TIMER0": {"type": "pwm", "channels": 3},
                               "IADC0": {"type": "adc", "channels": 16, "resolution_bits": 12},
                           })
    def get_sdk_include_paths(self) -> List[str]:
        gsdk = os.getenv("GSDK_PATH", "")
        return [f"{gsdk}/platform/emlib/inc", f"{gsdk}/platform/Device/SiliconLabs/EFR32MG24/Include"] if gsdk else []
    def get_template_files(self) -> Dict[str, str]:
        return {}
    def get_linker_script(self) -> Optional[str]:
        return None

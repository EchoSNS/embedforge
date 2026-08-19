"""Silicon Labs Gecko SDK driver catalog (emlib + RAIL)."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from plugins.base import ApiLayer, DriverCatalog, DriverInfo

_DRIVERS = [
    DriverInfo(name="em_usart", api_layer=ApiLayer.MID_LEVEL, peripheral="UART",
               description="USART driver (UART/SPI modes)", when_to_use="UART communication"),
    DriverInfo(name="em_eusart", api_layer=ApiLayer.MID_LEVEL, peripheral="UART",
               description="Enhanced USART (Series 2)", when_to_use="UART on EFR32xG2x"),
    DriverInfo(name="em_i2c", api_layer=ApiLayer.MID_LEVEL, peripheral="I2C",
               description="I2C master/slave driver", when_to_use="I2C communication"),
    DriverInfo(name="em_timer", api_layer=ApiLayer.MID_LEVEL, peripheral="PWM",
               description="Timer with PWM capability", when_to_use="PWM, timing"),
    DriverInfo(name="em_adc", api_layer=ApiLayer.MID_LEVEL, peripheral="ADC",
               description="ADC driver (Series 0/1)", when_to_use="Analog measurement"),
    DriverInfo(name="em_iadc", api_layer=ApiLayer.MID_LEVEL, peripheral="ADC",
               description="Incremental ADC (Series 2)", when_to_use="ADC on EFR32xG2x"),
    DriverInfo(name="em_gpio", api_layer=ApiLayer.MID_LEVEL, peripheral="GPIO",
               description="GPIO pin control", when_to_use="Digital I/O"),
]

class SiLabsDriverCatalog(DriverCatalog):
    def list_peripherals(self) -> List[str]:
        return sorted(set(d.peripheral for d in _DRIVERS))
    def list_drivers(self, peripheral: str) -> List[DriverInfo]:
        return [d for d in _DRIVERS if d.peripheral == peripheral.upper()]
    def get_driver(self, name: str) -> Optional[DriverInfo]:
        return next((d for d in _DRIVERS if d.name == name), None)
    def recommend_driver(self, peripheral: str, requirements: Dict[str, Any]) -> Optional[DriverInfo]:
        drivers = self.list_drivers(peripheral)
        return drivers[0] if drivers else None
    def get_driver_functions(self, driver_name: str) -> List[Dict[str, str]]:
        return []
    def get_driver_types(self, driver_name: str) -> List[Dict[str, str]]:
        return []

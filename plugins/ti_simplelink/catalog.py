"""TI SimpleLink driver catalog."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from plugins.base import ApiLayer, DriverCatalog, DriverInfo

_DRIVERS = [
    DriverInfo(name="UART2", api_layer=ApiLayer.HIGH_LEVEL, peripheral="UART",
               description="UART2 driver (replaces legacy UART driver)",
               when_to_use="Serial communication"),
    DriverInfo(name="SPI", api_layer=ApiLayer.HIGH_LEVEL, peripheral="SPI",
               description="SPI master/slave with DMA",
               when_to_use="SPI communication"),
    DriverInfo(name="I2C", api_layer=ApiLayer.HIGH_LEVEL, peripheral="I2C",
               description="I2C master driver",
               when_to_use="I2C sensor communication"),
    DriverInfo(name="PWM", api_layer=ApiLayer.HIGH_LEVEL, peripheral="PWM",
               description="PWM driver via GPTimer",
               when_to_use="PWM output"),
    DriverInfo(name="ADC", api_layer=ApiLayer.HIGH_LEVEL, peripheral="ADC",
               description="ADC single-channel driver",
               when_to_use="Analog measurement"),
    DriverInfo(name="GPIO", api_layer=ApiLayer.HIGH_LEVEL, peripheral="GPIO",
               description="GPIO with interrupt callbacks",
               when_to_use="Digital I/O, interrupt buttons"),
]

class TIDriverCatalog(DriverCatalog):
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

"""Microchip Harmony driver catalog."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from plugins.base import ApiLayer, DriverCatalog, DriverInfo

_DRIVERS = [
    DriverInfo(name="SERCOM_USART", api_layer=ApiLayer.HIGH_LEVEL, peripheral="UART",
               description="SERCOM USART PLIB/driver",
               when_to_use="UART on SAM D/E devices"),
    DriverInfo(name="SERCOM_SPI", api_layer=ApiLayer.HIGH_LEVEL, peripheral="SPI",
               description="SERCOM SPI master driver",
               when_to_use="SPI communication on SAM D/E"),
    DriverInfo(name="SERCOM_I2C", api_layer=ApiLayer.HIGH_LEVEL, peripheral="I2C",
               description="SERCOM I2C master driver",
               when_to_use="I2C communication on SAM D/E"),
    DriverInfo(name="TCC_PWM", api_layer=ApiLayer.HIGH_LEVEL, peripheral="PWM",
               description="TCC Timer PWM driver",
               when_to_use="PWM output on SAM D/E"),
    DriverInfo(name="ADC_PLIB", api_layer=ApiLayer.MID_LEVEL, peripheral="ADC",
               description="ADC peripheral library",
               when_to_use="Analog measurement"),
    DriverInfo(name="PORT_PLIB", api_layer=ApiLayer.MID_LEVEL, peripheral="GPIO",
               description="PORT GPIO driver",
               when_to_use="Digital I/O"),
]

class MicrochipDriverCatalog(DriverCatalog):
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

"""Renesas FSP driver catalog."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from plugins.base import ApiLayer, DriverCatalog, DriverInfo

_DRIVERS = [
    DriverInfo(name="r_sci_uart", api_layer=ApiLayer.HIGH_LEVEL, peripheral="UART",
               description="SCI UART driver with interrupt/DMA support",
               when_to_use="UART serial communication"),
    DriverInfo(name="r_spi", api_layer=ApiLayer.HIGH_LEVEL, peripheral="SPI",
               description="SPI master/slave driver",
               when_to_use="SPI communication"),
    DriverInfo(name="r_iic_master", api_layer=ApiLayer.HIGH_LEVEL, peripheral="I2C",
               description="IIC master driver",
               when_to_use="I2C sensor communication"),
    DriverInfo(name="r_gpt", api_layer=ApiLayer.HIGH_LEVEL, peripheral="PWM",
               description="General PWM Timer driver",
               when_to_use="PWM, input capture, timing"),
    DriverInfo(name="r_adc", api_layer=ApiLayer.HIGH_LEVEL, peripheral="ADC",
               description="ADC driver with scan group support",
               when_to_use="Analog measurement"),
    DriverInfo(name="r_ioport", api_layer=ApiLayer.HIGH_LEVEL, peripheral="GPIO",
               description="I/O port driver",
               when_to_use="GPIO digital I/O"),
    DriverInfo(name="r_can", api_layer=ApiLayer.HIGH_LEVEL, peripheral="CAN",
               description="CAN driver",
               when_to_use="CAN bus communication"),
]

class RenesasDriverCatalog(DriverCatalog):
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

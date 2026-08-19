"""AURIX iLLD driver catalog."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from plugins.base import ApiLayer, DriverCatalog, DriverInfo

_DRIVERS = [
    DriverInfo(name="IfxAsclin_Asc", api_layer=ApiLayer.HIGH_LEVEL, peripheral="UART",
               description="ASCLIN UART driver (async serial communication)",
               when_to_use="UART/LIN communication on AURIX"),
    DriverInfo(name="IfxQspi_SpiMaster", api_layer=ApiLayer.HIGH_LEVEL, peripheral="SPI",
               description="QSPI master driver",
               when_to_use="SPI communication"),
    DriverInfo(name="IfxI2c_I2c", api_layer=ApiLayer.HIGH_LEVEL, peripheral="I2C",
               description="I2C master driver",
               when_to_use="I2C sensor communication"),
    DriverInfo(name="IfxGtm_Tom_Pwm", api_layer=ApiLayer.HIGH_LEVEL, peripheral="PWM",
               description="GTM TOM PWM driver",
               when_to_use="PWM output via GTM timer"),
    DriverInfo(name="IfxVadc_Adc", api_layer=ApiLayer.HIGH_LEVEL, peripheral="ADC",
               description="VADC driver (versatile ADC)",
               when_to_use="Analog measurement"),
    DriverInfo(name="IfxPort_Io", api_layer=ApiLayer.HIGH_LEVEL, peripheral="GPIO",
               description="Port I/O driver",
               when_to_use="Digital I/O, LED, button"),
    DriverInfo(name="IfxMultican_Can", api_layer=ApiLayer.HIGH_LEVEL, peripheral="CAN",
               description="MultiCAN+ driver",
               when_to_use="CAN/CAN-FD communication"),
    DriverInfo(name="IfxGeth_Eth", api_layer=ApiLayer.HIGH_LEVEL, peripheral="ETHERNET",
               description="Gigabit Ethernet driver",
               when_to_use="Ethernet communication"),
    DriverInfo(name="IfxStm_Timer", api_layer=ApiLayer.HIGH_LEVEL, peripheral="TIMER",
               description="System Timer Module driver",
               when_to_use="System timing, delays"),
]

class AurixDriverCatalog(DriverCatalog):
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

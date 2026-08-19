"""Infineon ModusToolbox driver catalog (PDL + HAL)."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from plugins.base import ApiLayer, DriverCatalog, DriverInfo

_DRIVERS = [
    DriverInfo(name="cyhal_uart", api_layer=ApiLayer.HIGH_LEVEL, peripheral="UART",
               description="HAL UART driver with async support",
               when_to_use="Standard UART communication"),
    DriverInfo(name="cyhal_spi", api_layer=ApiLayer.HIGH_LEVEL, peripheral="SPI",
               description="HAL SPI master/slave driver",
               when_to_use="SPI communication"),
    DriverInfo(name="cyhal_i2c", api_layer=ApiLayer.HIGH_LEVEL, peripheral="I2C",
               description="HAL I2C master/slave driver",
               when_to_use="I2C sensor communication"),
    DriverInfo(name="cyhal_pwm", api_layer=ApiLayer.HIGH_LEVEL, peripheral="PWM",
               description="HAL PWM driver with dead-time",
               when_to_use="PWM output, motor control"),
    DriverInfo(name="cyhal_adc", api_layer=ApiLayer.HIGH_LEVEL, peripheral="ADC",
               description="HAL ADC driver",
               when_to_use="Analog measurement"),
    DriverInfo(name="cyhal_gpio", api_layer=ApiLayer.HIGH_LEVEL, peripheral="GPIO",
               description="HAL GPIO driver with interrupts",
               when_to_use="Digital I/O"),
    DriverInfo(name="cyhal_timer", api_layer=ApiLayer.HIGH_LEVEL, peripheral="TIMER",
               description="HAL Timer/Counter driver",
               when_to_use="Timing, counting"),
    DriverInfo(name="Cy_SCB_UART", api_layer=ApiLayer.MID_LEVEL, peripheral="UART",
               description="PDL SCB UART driver (low-level)",
               when_to_use="Advanced UART config not covered by HAL"),
]

class InfineonDriverCatalog(DriverCatalog):
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

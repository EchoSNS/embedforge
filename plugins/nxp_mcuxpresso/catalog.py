"""NXP MCUXpresso driver catalog."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from plugins.base import ApiLayer, DriverCatalog, DriverInfo

_DRIVERS = [
    DriverInfo(name="fsl_usart", api_layer=ApiLayer.HIGH_LEVEL, peripheral="UART",
               description="USART driver with blocking, interrupt, and DMA modes",
               when_to_use="Standard UART communication"),
    DriverInfo(name="fsl_spi", api_layer=ApiLayer.HIGH_LEVEL, peripheral="SPI",
               description="SPI master/slave driver",
               when_to_use="SPI communication with peripherals"),
    DriverInfo(name="fsl_i2c", api_layer=ApiLayer.HIGH_LEVEL, peripheral="I2C",
               description="I2C master/slave driver",
               when_to_use="I2C sensor/EEPROM communication"),
    DriverInfo(name="fsl_ctimer", api_layer=ApiLayer.HIGH_LEVEL, peripheral="PWM",
               description="CTimer for PWM and timing operations",
               when_to_use="PWM output or periodic interrupts"),
    DriverInfo(name="fsl_adc", api_layer=ApiLayer.HIGH_LEVEL, peripheral="ADC",
               description="ADC conversion driver",
               when_to_use="Analog signal measurement"),
    DriverInfo(name="fsl_gpio", api_layer=ApiLayer.HIGH_LEVEL, peripheral="GPIO",
               description="GPIO pin configuration and control",
               when_to_use="Digital I/O, LEDs, buttons"),
]


class NXPDriverCatalog(DriverCatalog):
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
        # Populated dynamically from SDK scan
        return []

    def get_driver_types(self, driver_name: str) -> List[Dict[str, str]]:
        return []

"""Nordic nRF Connect SDK driver catalog."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from plugins.base import ApiLayer, DriverCatalog, DriverInfo

_DRIVERS = [
    DriverInfo(name="nrfx_uarte", api_layer=ApiLayer.MID_LEVEL, peripheral="UART",
               description="UARTE driver (EasyDMA-based UART)",
               when_to_use="UART communication with DMA support"),
    DriverInfo(name="nrfx_spim", api_layer=ApiLayer.MID_LEVEL, peripheral="SPI",
               description="SPIM driver (SPI master with EasyDMA)",
               when_to_use="SPI master communication"),
    DriverInfo(name="nrfx_twim", api_layer=ApiLayer.MID_LEVEL, peripheral="I2C",
               description="TWIM driver (I2C master with EasyDMA)",
               when_to_use="I2C sensor communication"),
    DriverInfo(name="nrfx_pwm", api_layer=ApiLayer.MID_LEVEL, peripheral="PWM",
               description="PWM driver with sequence playback",
               when_to_use="LED control, servo, audio"),
    DriverInfo(name="nrfx_saadc", api_layer=ApiLayer.MID_LEVEL, peripheral="ADC",
               description="SAADC driver (successive approximation ADC)",
               when_to_use="Analog measurement, battery monitoring"),
    DriverInfo(name="nrfx_gpiote", api_layer=ApiLayer.MID_LEVEL, peripheral="GPIO",
               description="GPIOTE driver (GPIO tasks and events)",
               when_to_use="Pin interrupts, toggling via PPI"),
    DriverInfo(name="nrfx_timer", api_layer=ApiLayer.MID_LEVEL, peripheral="TIMER",
               description="Timer/counter driver",
               when_to_use="Timing, counting, periodic interrupts"),
]


class NordicDriverCatalog(DriverCatalog):
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

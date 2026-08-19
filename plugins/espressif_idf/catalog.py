"""ESP-IDF driver catalog."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from plugins.base import ApiLayer, DriverCatalog, DriverInfo

_DRIVERS = [
    DriverInfo(name="driver/uart", api_layer=ApiLayer.HIGH_LEVEL, peripheral="UART",
               description="UART driver with ring buffer and event-driven reception",
               when_to_use="Serial communication (RS232/RS485/debug)"),
    DriverInfo(name="driver/spi_master", api_layer=ApiLayer.HIGH_LEVEL, peripheral="SPI",
               description="SPI master driver with DMA and queued transactions",
               when_to_use="SPI communication with external devices"),
    DriverInfo(name="driver/i2c", api_layer=ApiLayer.HIGH_LEVEL, peripheral="I2C",
               description="I2C master/slave driver",
               when_to_use="I2C sensor and peripheral communication"),
    DriverInfo(name="driver/ledc", api_layer=ApiLayer.HIGH_LEVEL, peripheral="PWM",
               description="LED controller (PWM) with hardware fade",
               when_to_use="PWM output, LED dimming, simple motor control"),
    DriverInfo(name="driver/mcpwm", api_layer=ApiLayer.HIGH_LEVEL, peripheral="PWM",
               description="Motor Control PWM with dead-time and fault detection",
               when_to_use="BLDC/stepper motor control, complementary PWM"),
    DriverInfo(name="esp_adc/adc_oneshot", api_layer=ApiLayer.HIGH_LEVEL, peripheral="ADC",
               description="ADC one-shot reading driver",
               when_to_use="Single analog measurement"),
    DriverInfo(name="esp_adc/adc_continuous", api_layer=ApiLayer.HIGH_LEVEL, peripheral="ADC",
               description="ADC continuous (DMA) conversion driver",
               when_to_use="High-speed analog sampling"),
    DriverInfo(name="driver/gpio", api_layer=ApiLayer.HIGH_LEVEL, peripheral="GPIO",
               description="GPIO driver with interrupt support",
               when_to_use="Digital I/O, interrupt-driven buttons"),
    DriverInfo(name="driver/gptimer", api_layer=ApiLayer.HIGH_LEVEL, peripheral="TIMER",
               description="General purpose timer driver",
               when_to_use="Periodic interrupts, timing measurement"),
    DriverInfo(name="driver/twai", api_layer=ApiLayer.HIGH_LEVEL, peripheral="CAN",
               description="Two-Wire Automotive Interface (CAN 2.0)",
               when_to_use="CAN bus communication"),
]


class ESPDriverCatalog(DriverCatalog):
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

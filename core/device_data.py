"""
Device Data Model — universal schema for MCU hardware knowledge.

Represents pin-mux tables, peripheral instances, and register maps
in a vendor-agnostic format. Populated by vendor-specific importers
(CubeMX XML, ATDF, SVD, devicetree, CMSIS-Pack).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PinDirection(str, Enum):
    INPUT = "input"
    OUTPUT = "output"
    BIDIRECTIONAL = "bidirectional"
    ANALOG = "analog"
    POWER = "power"


@dataclass(frozen=True)
class PinMuxEntry:
    """One alternate-function assignment for a physical pin."""

    pin_name: str           # e.g. "PA2", "P0.06", "GPIO_AD_B0_03"
    port: str               # e.g. "A", "0", "AD_B0"
    pin_number: int         # port-relative index (0-15 for STM32, 0-31 for nRF)
    af_number: int          # alternate function index (0-15 for STM32, -1 if N/A)
    signal: str             # e.g. "USART2_TX", "TIM1_CH1", "SPI0_MOSI"
    peripheral: str         # e.g. "USART2", "TIM1", "SPI0"
    peripheral_type: str    # e.g. "UART", "PWM", "SPI", "ADC", "GPIO"
    direction: PinDirection = PinDirection.BIDIRECTIONAL
    notes: str = ""


@dataclass(frozen=True)
class PeripheralInstance:
    """A specific peripheral instance on the device."""

    name: str               # e.g. "USART2", "TIM1", "ADC1"
    peripheral_type: str    # e.g. "UART", "PWM", "ADC"
    bus: str = ""           # e.g. "APB1", "AHB1"
    base_address: int = 0
    irq_names: tuple = ()   # e.g. ("USART2_IRQn",)
    features: tuple = ()    # e.g. ("complementary", "dead_time")


@dataclass(frozen=True)
class RegisterField:
    """A bit field within a register."""

    name: str
    bit_offset: int
    bit_width: int
    access: str = "read-write"  # "read-only", "write-only", "read-write"
    description: str = ""
    reset_value: int = 0


@dataclass(frozen=True)
class Register:
    """A single peripheral register."""

    name: str
    offset: int
    size: int = 32          # bits
    access: str = "read-write"
    description: str = ""
    reset_value: int = 0
    fields: tuple = ()      # tuple[RegisterField, ...]


@dataclass
class DeviceInfo:
    """Complete hardware description of a specific MCU device + package."""

    vendor: str             # e.g. "STMicroelectronics", "Nordic", "NXP"
    family: str             # e.g. "STM32F4", "nRF52", "LPC55"
    device: str             # e.g. "STM32F446RETx", "nRF52840"
    package: str            # e.g. "LQFP64", "QFN48"
    core: str = ""          # e.g. "Cortex-M4", "Cortex-M33"
    max_clock_hz: int = 0

    pin_mux: List[PinMuxEntry] = field(default_factory=list)
    peripherals: List[PeripheralInstance] = field(default_factory=list)
    registers: Dict[str, List[Register]] = field(default_factory=dict)

    # Metadata
    source_file: str = ""   # path to the file this was imported from
    source_format: str = "" # "cubemx", "svd", "atdf", "devicetree", "cmsis_pack"

    def get_pins_for_peripheral(self, peripheral_name: str) -> List[PinMuxEntry]:
        return [p for p in self.pin_mux if p.peripheral == peripheral_name]

    def get_pins_for_type(self, peripheral_type: str) -> List[PinMuxEntry]:
        return [p for p in self.pin_mux if p.peripheral_type == peripheral_type.upper()]

    def get_pins_for_signal(self, signal: str) -> List[PinMuxEntry]:
        return [p for p in self.pin_mux if signal.upper() in p.signal.upper()]

    def get_peripheral_instances(self, peripheral_type: str) -> List[PeripheralInstance]:
        return [p for p in self.peripherals if p.peripheral_type == peripheral_type.upper()]

    def get_registers_for(self, peripheral_name: str) -> List[Register]:
        return self.registers.get(peripheral_name, [])

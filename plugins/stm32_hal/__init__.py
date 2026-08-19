"""STM32 HAL Plugin — example vendor SDK integration for EmbedForge."""

from plugins.stm32_hal.catalog import STM32DriverCatalog
from plugins.stm32_hal.pins import STM32PinProvider
from plugins.stm32_hal.compiler import ARMGCCCompiler
from plugins.stm32_hal.rules import STM32ArchitectureRules
from plugins.stm32_hal.boards import NucleoF446RE

from plugins.base import PluginManifest

MANIFEST = PluginManifest(
    name="stm32_hal",
    version="1.0.0",
    vendor="STMicroelectronics (community)",
    description="STM32 HAL driver plugin for Cortex-M MCUs",
    supported_mcus=["STM32F446", "STM32F407", "STM32G474", "STM32L476"],
    driver_catalog_class="plugins.stm32_hal.catalog.STM32DriverCatalog",
    pin_provider_class="plugins.stm32_hal.pins.STM32PinProvider",
    compiler_backend_class="plugins.stm32_hal.compiler.ARMGCCCompiler",
    architecture_rules_class="plugins.stm32_hal.rules.STM32ArchitectureRules",
    board_template_classes={
        "NUCLEO-F446RE": "plugins.stm32_hal.boards.NucleoF446RE",
    },
    project_exporter_class="plugins.stm32_hal.exporter.STM32ProjectExporter",
)


def register(registry):
    """Auto-registration hook called by plugin loader."""
    registry.register(MANIFEST)

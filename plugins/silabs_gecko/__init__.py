"""Silicon Labs Gecko SDK Plugin — EFM32, EFR32 families."""
from plugins.base import PluginManifest

MANIFEST = PluginManifest(
    name="silabs_gecko",
    version="0.1.0",
    vendor="Silicon Laboratories",
    description="Gecko SDK plugin for EFM32/EFR32 (Cortex-M0+/M4/M33)",
    supported_mcus=["EFM32GG", "EFR32MG", "EFR32BG", "EFM32PG"],
    driver_catalog_class="plugins.silabs_gecko.catalog.SiLabsDriverCatalog",
    pin_provider_class="plugins.silabs_gecko.pins.SiLabsPinProvider",
    compiler_backend_class="plugins.silabs_gecko.compiler.ARMGCCCompiler",
    architecture_rules_class="plugins.silabs_gecko.rules.SiLabsArchitectureRules",
    board_template_classes={
        "BRD4187C": "plugins.silabs_gecko.boards.BRD4187C",
    },
)

def register(registry):
    registry.register(MANIFEST)

"""Microchip MPLAB Harmony Plugin — SAM and PIC32 families."""
from plugins.base import PluginManifest

MANIFEST = PluginManifest(
    name="microchip_harmony",
    version="0.1.0",
    vendor="Microchip Technology",
    description="MPLAB Harmony v3 plugin for SAM and PIC32 MCUs",
    supported_mcus=["ATSAMD21", "ATSAMD51", "ATSAME54", "PIC32MZ"],
    driver_catalog_class="plugins.microchip_harmony.catalog.MicrochipDriverCatalog",
    pin_provider_class="plugins.microchip_harmony.pins.MicrochipPinProvider",
    compiler_backend_class="plugins.microchip_harmony.compiler.ARMGCCCompiler",
    architecture_rules_class="plugins.microchip_harmony.rules.MicrochipArchitectureRules",
    board_template_classes={
        "SAM-E54-Xplained-Pro": "plugins.microchip_harmony.boards.SAME54Xplained",
    },
)

def register(registry):
    registry.register(MANIFEST)

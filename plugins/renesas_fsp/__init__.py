"""Renesas FSP Plugin — RA family (Cortex-M33/M4/M23)."""
from plugins.base import PluginManifest

MANIFEST = PluginManifest(
    name="renesas_fsp",
    version="0.1.0",
    vendor="Renesas Electronics",
    description="Flexible Software Package plugin for Renesas RA MCUs",
    supported_mcus=["RA6M5", "RA6M4", "RA4M1", "RA2L1"],
    driver_catalog_class="plugins.renesas_fsp.catalog.RenesasDriverCatalog",
    pin_provider_class="plugins.renesas_fsp.pins.RenesasPinProvider",
    compiler_backend_class="plugins.renesas_fsp.compiler.ARMGCCCompiler",
    architecture_rules_class="plugins.renesas_fsp.rules.RenesasArchitectureRules",
    board_template_classes={
        "EK-RA6M5": "plugins.renesas_fsp.boards.EKRA6M5",
    },
)

def register(registry):
    registry.register(MANIFEST)

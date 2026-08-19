"""Infineon ModusToolbox Plugin — PSoC 6, XMC, and AIROC families."""

from plugins.base import PluginManifest

MANIFEST = PluginManifest(
    name="infineon_mtb",
    version="0.1.0",
    vendor="Infineon Technologies",
    description="ModusToolbox plugin for PSoC 6, XMC, and AIROC (Cortex-M0+/M4/M33)",
    supported_mcus=["CY8C6xx", "XMC4xxx", "XMC1xxx", "CYW43xxx"],
    driver_catalog_class="plugins.infineon_mtb.catalog.InfineonDriverCatalog",
    pin_provider_class="plugins.infineon_mtb.pins.InfineonPinProvider",
    compiler_backend_class="plugins.infineon_mtb.compiler.ARMGCCCompiler",
    architecture_rules_class="plugins.infineon_mtb.rules.InfineonArchitectureRules",
    board_template_classes={
        "CY8CPROTO-062-4343W": "plugins.infineon_mtb.boards.CY8CProto062",
    },
)

def register(registry):
    registry.register(MANIFEST)

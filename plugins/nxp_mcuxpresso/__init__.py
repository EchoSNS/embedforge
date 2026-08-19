"""NXP MCUXpresso SDK Plugin — support for LPC, i.MX RT, and Kinetis families."""

from plugins.base import PluginManifest


MANIFEST = PluginManifest(
    name="nxp_mcuxpresso",
    version="0.1.0",
    vendor="NXP Semiconductors",
    description="NXP MCUXpresso SDK plugin for Cortex-M MCUs (LPC, i.MX RT, Kinetis)",
    supported_mcus=["LPC55S69", "MIMXRT1062", "MK64F"],
    driver_catalog_class="plugins.nxp_mcuxpresso.catalog.NXPDriverCatalog",
    pin_provider_class="plugins.nxp_mcuxpresso.pins.NXPPinProvider",
    compiler_backend_class="plugins.nxp_mcuxpresso.compiler.ARMGCCCompiler",
    architecture_rules_class="plugins.nxp_mcuxpresso.rules.NXPArchitectureRules",
    board_template_classes={
        "LPCXpresso55S69": "plugins.nxp_mcuxpresso.boards.LPCXpresso55S69",
    },
)


def register(registry):
    registry.register(MANIFEST)

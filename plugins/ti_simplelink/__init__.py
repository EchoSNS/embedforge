"""Texas Instruments SimpleLink SDK Plugin — CC26xx, MSP432, TM4C."""
from plugins.base import PluginManifest

MANIFEST = PluginManifest(
    name="ti_simplelink",
    version="0.1.0",
    vendor="Texas Instruments",
    description="SimpleLink SDK plugin for TI wireless MCUs and MSP432",
    supported_mcus=["CC2652R", "CC1352P", "MSP432P4", "TM4C123"],
    driver_catalog_class="plugins.ti_simplelink.catalog.TIDriverCatalog",
    pin_provider_class="plugins.ti_simplelink.pins.TIPinProvider",
    compiler_backend_class="plugins.ti_simplelink.compiler.ARMGCCCompiler",
    architecture_rules_class="plugins.ti_simplelink.rules.TIArchitectureRules",
    board_template_classes={
        "CC26X2R1-LAUNCHXL": "plugins.ti_simplelink.boards.CC26X2RLaunchpad",
    },
)

def register(registry):
    registry.register(MANIFEST)

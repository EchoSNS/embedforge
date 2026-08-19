"""Nordic nRF Connect SDK Plugin — support for nRF52, nRF53, nRF91 families."""

from plugins.base import PluginManifest


MANIFEST = PluginManifest(
    name="nordic_nrfconnect",
    version="0.1.0",
    vendor="Nordic Semiconductor",
    description="nRF Connect SDK plugin for Nordic BLE/cellular MCUs",
    supported_mcus=["nRF52840", "nRF52833", "nRF5340", "nRF9160"],
    driver_catalog_class="plugins.nordic_nrfconnect.catalog.NordicDriverCatalog",
    pin_provider_class="plugins.nordic_nrfconnect.pins.NordicPinProvider",
    compiler_backend_class="plugins.nordic_nrfconnect.compiler.ARMGCCCompiler",
    architecture_rules_class="plugins.nordic_nrfconnect.rules.NordicArchitectureRules",
    board_template_classes={
        "nRF52840-DK": "plugins.nordic_nrfconnect.boards.NRF52840DK",
    },
)


def register(registry):
    registry.register(MANIFEST)

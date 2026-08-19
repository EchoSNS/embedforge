"""Infineon AURIX Plugin — TriCore TC3xx/TC4xx families (iLLD drivers)."""
from plugins.base import PluginManifest

MANIFEST = PluginManifest(
    name="infineon_aurix",
    version="0.1.0",
    vendor="Infineon Technologies",
    description="AURIX TriCore plugin for TC3xx/TC4xx MCUs (iLLD Low Level Drivers)",
    supported_mcus=["TC375", "TC397", "TC4D7"],
    driver_catalog_class="plugins.infineon_aurix.catalog.AurixDriverCatalog",
    pin_provider_class="plugins.infineon_aurix.pins.AurixPinProvider",
    compiler_backend_class="plugins.infineon_aurix.compiler.TriCoreCompiler",
    architecture_rules_class="plugins.infineon_aurix.rules.AurixArchitectureRules",
    board_template_classes={
        "AURIX-TC4D7-LiteKit": "plugins.infineon_aurix.boards.TC4D7LiteKit",
    },
    project_exporter_class="plugins.infineon_aurix.exporter.AurixProjectExporter",
)

def register(registry):
    registry.register(MANIFEST)

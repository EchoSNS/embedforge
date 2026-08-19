"""Espressif ESP-IDF Plugin — support for ESP32, ESP32-S3, ESP32-C3."""

from plugins.base import PluginManifest


MANIFEST = PluginManifest(
    name="espressif_idf",
    version="0.1.0",
    vendor="Espressif Systems",
    description="ESP-IDF plugin for ESP32 series (Xtensa and RISC-V)",
    supported_mcus=["ESP32", "ESP32-S3", "ESP32-C3", "ESP32-C6", "ESP32-H2"],
    driver_catalog_class="plugins.espressif_idf.catalog.ESPDriverCatalog",
    pin_provider_class="plugins.espressif_idf.pins.ESPPinProvider",
    compiler_backend_class="plugins.espressif_idf.compiler.ESPCompiler",
    architecture_rules_class="plugins.espressif_idf.rules.ESPArchitectureRules",
    board_template_classes={
        "ESP32-DevKitC": "plugins.espressif_idf.boards.ESP32DevKitC",
    },
)


def register(registry):
    registry.register(MANIFEST)

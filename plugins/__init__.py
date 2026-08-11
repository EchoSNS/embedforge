"""EmbedForge Plugin System — vendor SDK integration layer."""

from plugins.base import (
    DriverCatalog,
    PinCapabilityProvider,
    CompilerBackend,
    ArchitectureRulePack,
    BoardTemplate,
    PluginManifest,
    PluginRegistry,
)

__all__ = [
    "DriverCatalog",
    "PinCapabilityProvider",
    "CompilerBackend",
    "ArchitectureRulePack",
    "BoardTemplate",
    "PluginManifest",
    "PluginRegistry",
]

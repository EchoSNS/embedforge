"""
Plugin Base Interfaces — contracts that every vendor SDK plugin must implement.

Design Principles:
  - Interface Segregation: each interface is minimal and focused
  - Dependency Inversion: core depends on abstractions, not vendor specifics
  - Open/Closed: new vendors added without modifying core logic
"""

from __future__ import annotations

import importlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# =============================================================================
# Value Objects
# =============================================================================


class ApiLayer(Enum):
    """Abstraction layers within an SDK driver hierarchy."""

    UNIFIED = "unified"
    HIGH_LEVEL = "high_level"
    MID_LEVEL = "mid_level"
    LOW_LEVEL = "low_level"
    SUPPORT = "support"


@dataclass(frozen=True)
class DriverInfo:
    """Immutable description of a single SDK driver/API module."""

    name: str
    api_layer: ApiLayer
    peripheral: str
    description: str = ""
    supersedes: tuple[str, ...] = ()
    superseded_by: tuple[str, ...] = ()
    handles_internally: tuple[str, ...] = ()
    user_must_handle: tuple[str, ...] = ()
    when_to_use: str = ""
    when_not_to_use: str = ""
    companion_drivers: tuple[str, ...] = ()


@dataclass(frozen=True)
class PinMapping:
    """A validated pin assignment on a target MCU."""

    symbol: str
    port: str
    pin: int
    peripheral: str
    function: str
    alternate_function: int = 0
    is_complementary: bool = False


@dataclass(frozen=True)
class CompilationResult:
    """Outcome of a single compilation attempt."""

    success: bool
    output_file: Optional[str] = None
    stdout: str = ""
    stderr: str = ""
    errors: tuple[Dict[str, Any], ...] = ()
    warnings: tuple[Dict[str, Any], ...] = ()
    command: str = ""


@dataclass
class BoardConfig:
    """Board-level configuration metadata."""

    name: str
    mcu: str
    mcu_family: str
    clock_hz: int
    pin_mappings: Dict[str, List[PinMapping]] = field(default_factory=dict)
    peripherals: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    linker_script: Optional[str] = None
    startup_file: Optional[str] = None


# =============================================================================
# Plugin Interfaces (Abstract Base Classes)
# =============================================================================


class DriverCatalog(ABC):
    """
    Registry of available drivers/API modules from a vendor SDK.

    Responsibilities:
      - Enumerate available drivers for a peripheral type
      - Resolve the best driver given complexity/use-case requirements
      - Provide driver metadata (signatures, includes, config structs)
    """

    @abstractmethod
    def list_peripherals(self) -> List[str]:
        """Return all peripheral categories this catalog covers (e.g. PWM, ADC, UART)."""

    @abstractmethod
    def list_drivers(self, peripheral: str) -> List[DriverInfo]:
        """Return all known drivers for a peripheral, ordered by abstraction level."""

    @abstractmethod
    def get_driver(self, name: str) -> Optional[DriverInfo]:
        """Look up a specific driver by name."""

    @abstractmethod
    def recommend_driver(
        self, peripheral: str, requirements: Dict[str, Any]
    ) -> Optional[DriverInfo]:
        """
        Recommend the best driver for a peripheral given use-case requirements.

        Args:
            peripheral: Peripheral category (e.g. "PWM", "ADC").
            requirements: Dict describing complexity, channel count, etc.
        """

    @abstractmethod
    def get_driver_functions(self, driver_name: str) -> List[Dict[str, str]]:
        """Return function signatures for a driver (name, signature, description)."""

    @abstractmethod
    def get_driver_types(self, driver_name: str) -> List[Dict[str, str]]:
        """Return struct/enum type definitions for a driver."""


class PinCapabilityProvider(ABC):
    """
    Pin/peripheral capability lookups for a specific MCU.

    Responsibilities:
      - Validate that a pin symbol exists on the target MCU
      - Enumerate available pins for a peripheral function
      - Resolve conflicts (pin already assigned)
    """

    @abstractmethod
    def get_available_pins(self, peripheral: str, function: str = "") -> List[PinMapping]:
        """
        List all pins capable of a given peripheral function.

        Args:
            peripheral: e.g. "TIM", "ADC", "UART"
            function: optional sub-function filter (e.g. "CH1", "TX")
        """

    @abstractmethod
    def validate_pin(self, symbol: str) -> bool:
        """Return True if the pin symbol is valid on this MCU."""

    @abstractmethod
    def validate_assignment(
        self, assignments: Dict[str, str]
    ) -> List[str]:
        """
        Validate a set of pin assignments. Return list of error messages (empty = valid).

        Args:
            assignments: mapping of function_name → pin_symbol
        """

    @abstractmethod
    def get_pin_patterns(self) -> Dict[str, str]:
        """Return regex patterns for recognizable pin symbols in generated code."""


class CompilerBackend(ABC):
    """
    Abstraction over a cross-compiler toolchain.

    Responsibilities:
      - Discover/validate toolchain availability
      - Compile source files for the target MCU
      - Parse errors/warnings into structured format
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the compiler toolchain is installed and accessible."""

    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Return metadata about the compiler (type, version, target arch)."""

    @abstractmethod
    def compile(
        self,
        source_files: List[str],
        include_paths: List[str],
        output_path: str,
        target_mcu: str = "",
        extra_flags: Optional[List[str]] = None,
    ) -> CompilationResult:
        """
        Compile source files and return structured result.

        Args:
            source_files: paths to .c files
            include_paths: -I directories
            output_path: where to write output binary/object
            target_mcu: MCU identifier for target-specific flags
            extra_flags: additional compiler flags
        """

    @abstractmethod
    def parse_errors(self, stderr: str) -> List[Dict[str, Any]]:
        """Parse compiler stderr into structured error dicts with file, line, message."""


class ArchitectureRulePack(ABC):
    """
    Coding conventions and architectural rules for a specific SDK.

    Responsibilities:
      - Provide rules that constrain code generation (naming, init patterns, etc.)
      - Validate generated code against SDK conventions
      - Supply example patterns the LLM should follow
    """

    @abstractmethod
    def get_rules_text(self) -> str:
        """Return a formatted text block of all architecture rules for LLM injection."""

    @abstractmethod
    def get_init_pattern(self, driver_name: str) -> str:
        """Return the canonical initialization pattern for a driver."""

    @abstractmethod
    def get_naming_conventions(self) -> Dict[str, str]:
        """Return naming convention rules (prefix style, case, etc.)."""

    @abstractmethod
    def validate_code(self, code: str) -> List[str]:
        """
        Check generated code against architecture rules.

        Returns list of violations (empty = compliant).
        """


class BoardTemplate(ABC):
    """
    Board-level configuration and template file provider.

    Responsibilities:
      - Supply board metadata (MCU, clock, default pins)
      - Provide template/skeleton project files
      - Resolve SDK header paths for the board
    """

    @abstractmethod
    def get_config(self) -> BoardConfig:
        """Return the board's configuration metadata."""

    @abstractmethod
    def get_sdk_include_paths(self) -> List[str]:
        """Return include paths for the SDK headers on this board."""

    @abstractmethod
    def get_template_files(self) -> Dict[str, str]:
        """Return skeleton project files (filename → content)."""

    @abstractmethod
    def get_linker_script(self) -> Optional[str]:
        """Return linker script content, or None if not applicable."""


# =============================================================================
# Plugin Manifest & Registry
# =============================================================================


@dataclass
class PluginManifest:
    """Declares what a plugin provides."""

    name: str
    version: str
    vendor: str
    description: str
    supported_mcus: List[str]
    driver_catalog_class: str
    pin_provider_class: str
    compiler_backend_class: str
    architecture_rules_class: str
    board_template_classes: Dict[str, str] = field(default_factory=dict)


class PluginRegistry:
    """
    Discovers and loads SDK plugins at runtime.

    Follows the Service Locator pattern — core modules request capabilities
    by interface type, the registry resolves to the active plugin's implementation.
    """

    def __init__(self) -> None:
        self._plugins: Dict[str, PluginManifest] = {}
        self._active_plugin: Optional[str] = None
        self._instances: Dict[str, Any] = {}

    def register(self, manifest: PluginManifest) -> None:
        self._plugins[manifest.name] = manifest
        logger.info(f"Registered plugin: {manifest.name} v{manifest.version}")

    def activate(self, plugin_name: str) -> None:
        if plugin_name not in self._plugins:
            raise ValueError(f"Plugin '{plugin_name}' not registered")
        self._active_plugin = plugin_name
        self._instances.clear()
        logger.info(f"Activated plugin: {plugin_name}")

    @property
    def active(self) -> Optional[PluginManifest]:
        if self._active_plugin:
            return self._plugins[self._active_plugin]
        return None

    def get_driver_catalog(self) -> DriverCatalog:
        return self._resolve("driver_catalog_class")

    def get_pin_provider(self) -> PinCapabilityProvider:
        return self._resolve("pin_provider_class")

    def get_compiler(self) -> CompilerBackend:
        return self._resolve("compiler_backend_class")

    def get_architecture_rules(self) -> ArchitectureRulePack:
        return self._resolve("architecture_rules_class")

    def get_board_template(self, board_name: str) -> BoardTemplate:
        manifest = self._require_active()
        class_path = manifest.board_template_classes.get(board_name)
        if not class_path:
            raise ValueError(
                f"Board '{board_name}' not found in plugin '{manifest.name}'. "
                f"Available: {list(manifest.board_template_classes.keys())}"
            )
        return self._instantiate(class_path)

    def list_boards(self) -> List[str]:
        manifest = self._require_active()
        return list(manifest.board_template_classes.keys())

    def _require_active(self) -> PluginManifest:
        if not self._active_plugin or self._active_plugin not in self._plugins:
            raise RuntimeError("No active plugin. Call registry.activate('plugin_name') first.")
        return self._plugins[self._active_plugin]

    def _resolve(self, attr: str) -> Any:
        manifest = self._require_active()
        class_path = getattr(manifest, attr)
        return self._instantiate(class_path)

    def _instantiate(self, class_path: str) -> Any:
        if class_path in self._instances:
            return self._instances[class_path]

        module_path, class_name = class_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        instance = cls()
        self._instances[class_path] = instance
        return instance

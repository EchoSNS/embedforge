# Plugin Development Guide

This guide explains how to create a custom SDK plugin for EmbedForge.

## Overview

A plugin provides EmbedForge with everything it needs to know about your vendor SDK:
- What drivers/APIs exist and when to use them
- What pins are available on your MCU/board
- How to compile code for your target
- What coding conventions to follow
- Board-level configuration (clock, peripherals, skeleton files)

## Plugin Structure

```
plugins/your_sdk/
├── __init__.py       # Manifest + register() hook
├── catalog.py        # DriverCatalog implementation
├── pins.py           # PinCapabilityProvider implementation
├── compiler.py       # CompilerBackend implementation
├── rules.py          # ArchitectureRulePack implementation
└── boards.py         # BoardTemplate implementations
```

## Step 1: Create the Manifest

`plugins/your_sdk/__init__.py`:

```python
from plugins.base import PluginManifest

MANIFEST = PluginManifest(
    name="your_sdk",
    version="1.0.0",
    vendor="Your Vendor",
    description="Your SDK plugin for EmbedForge",
    supported_mcus=["MCU_A", "MCU_B"],
    driver_catalog_class="plugins.your_sdk.catalog.YourDriverCatalog",
    pin_provider_class="plugins.your_sdk.pins.YourPinProvider",
    compiler_backend_class="plugins.your_sdk.compiler.YourCompiler",
    architecture_rules_class="plugins.your_sdk.rules.YourRules",
    board_template_classes={
        "YOUR_BOARD_1": "plugins.your_sdk.boards.YourBoard1",
    },
)

def register(registry):
    registry.register(MANIFEST)
```

## Step 2: Implement DriverCatalog

The catalog tells EmbedForge what SDK drivers exist for each peripheral.

```python
from plugins.base import ApiLayer, DriverCatalog, DriverInfo

class YourDriverCatalog(DriverCatalog):
    def list_peripherals(self) -> list[str]:
        return ["GPIO", "PWM", "ADC", "UART"]

    def list_drivers(self, peripheral: str) -> list[DriverInfo]:
        # Return drivers for this peripheral, ordered by abstraction level
        ...

    def get_driver(self, name: str) -> DriverInfo | None:
        ...

    def recommend_driver(self, peripheral: str, requirements: dict) -> DriverInfo | None:
        # Apply your selection logic (complexity, features, etc.)
        ...

    def get_driver_functions(self, driver_name: str) -> list[dict]:
        # Return [{"name": "...", "signature": "..."}]
        ...

    def get_driver_types(self, driver_name: str) -> list[dict]:
        # Return [{"name": "...", "kind": "struct|enum"}]
        ...
```

**Tips:**
- Include ALL public functions for each driver (the LLM uses these to generate correct code)
- Add `when_to_use` / `when_not_to_use` guidance — this helps the AI select correctly
- Mark deprecated drivers with `superseded_by`

## Step 3: Implement PinCapabilityProvider

```python
from plugins.base import PinCapabilityProvider, PinMapping

class YourPinProvider(PinCapabilityProvider):
    def get_available_pins(self, peripheral: str, function: str = "") -> list[PinMapping]:
        # Return all pins for this peripheral/function
        ...

    def validate_pin(self, symbol: str) -> bool:
        # Return True if this pin symbol exists on the MCU
        ...

    def validate_assignment(self, assignments: dict[str, str]) -> list[str]:
        # Check for conflicts, invalid pins — return error messages
        ...

    def get_pin_patterns(self) -> dict[str, str]:
        # Regex patterns to find pin references in generated code
        return {"gpio": r"P[A-H]\d+", "timer": r"TIM\d+_CH\d+"}
```

**Tips:**
- Include ALL alternate functions for each pin
- Pin validation prevents the most common class of code generation errors

## Step 4: Implement CompilerBackend

```python
from plugins.base import CompilationResult, CompilerBackend

class YourCompiler(CompilerBackend):
    def is_available(self) -> bool:
        # Check if toolchain is installed (shutil.which, path check, etc.)
        ...

    def get_info(self) -> dict:
        return {"available": True, "type": "your-gcc", "version": "..."}

    def compile(self, source_files, include_paths, output_path, target_mcu="", extra_flags=None) -> CompilationResult:
        # Run the compiler subprocess
        ...

    def parse_errors(self, stderr: str) -> list[dict]:
        # Parse "file:line:col: error: message" format
        ...
```

## Step 5: Implement ArchitectureRulePack

```python
from plugins.base import ArchitectureRulePack

class YourRules(ArchitectureRulePack):
    def get_rules_text(self) -> str:
        return """
        1. Always call SDK_Init() before using any peripheral
        2. Use handle-based API: SDK_Peripheral_Init(&handle)
        3. Enable clock before peripheral use
        ...
        """

    def get_init_pattern(self, driver_name: str) -> str:
        # Return canonical init code for this driver
        ...

    def get_naming_conventions(self) -> dict[str, str]:
        return {
            "function_prefix": "SDK_",
            "handle_naming": "h<peripheral>",
            "file_naming": "sdk_<module>.c",
        }

    def validate_code(self, code: str) -> list[str]:
        # Check generated code against your rules
        violations = []
        if "SDK_Init" not in code and "peripheral" in code.lower():
            violations.append("Missing SDK_Init() call")
        return violations
```

## Step 6: Implement BoardTemplate

```python
from plugins.base import BoardConfig, BoardTemplate

class YourBoard1(BoardTemplate):
    def get_config(self) -> BoardConfig:
        return BoardConfig(
            name="YOUR_BOARD_1",
            mcu="MCU_A",
            mcu_family="MCU_Family",
            clock_hz=100_000_000,
            peripherals={"TIM1": {"channels": 4}, "ADC1": {"channels": 8}},
        )

    def get_sdk_include_paths(self) -> list[str]:
        # Where the SDK headers live on disk
        ...

    def get_template_files(self) -> dict[str, str]:
        # Skeleton project files
        return {"main.c": "...", "startup.s": "..."}

    def get_linker_script(self) -> str | None:
        return "MEMORY { FLASH: ... RAM: ... }"
```

## Step 7: Activate Your Plugin

In `.env`:
```
EMBEDFORGE_PLUGIN=your_sdk
```

## Testing Your Plugin

```python
from plugins.base import PluginRegistry
from plugins.your_sdk import MANIFEST, register

registry = PluginRegistry()
register(registry)
registry.activate("your_sdk")

# Test driver catalog
catalog = registry.get_driver_catalog()
assert "GPIO" in catalog.list_peripherals()

# Test pin provider
pins = registry.get_pin_provider()
assert pins.validate_pin("PA0")

# Test rules
rules = registry.get_architecture_rules()
assert rules.get_rules_text()  # non-empty
```

## Reference: Plugin Interface Summary

| Interface | Methods | Purpose |
|-----------|---------|---------|
| `DriverCatalog` | 6 methods | SDK driver registry and recommendation |
| `PinCapabilityProvider` | 4 methods | Pin validation and enumeration |
| `CompilerBackend` | 4 methods | Compilation and error parsing |
| `ArchitectureRulePack` | 4 methods | Coding rules and validation |
| `BoardTemplate` | 4 methods | Board config and skeleton files |

See `plugins/stm32_hal/` for a complete working reference implementation.

"""Nordic nRF Connect SDK architecture rules."""

from __future__ import annotations

from typing import Any, Dict, List

from plugins.base import ArchitectureRulePack


class NordicArchitectureRules(ArchitectureRulePack):
    def get_rules_text(self) -> str:
        return "\n".join([
            "Nordic nRF Connect SDK / nrfx Architecture Rules:",
            "1. Include nrfx_<periph>.h for peripheral drivers.",
            "2. Initialize with nrfx_<periph>_init(&config, event_handler).",
            "3. Pin selection via nrfx config struct .psel fields (use NRF_GPIO_PIN_MAP(port, pin)).",
            "4. nRF52/53 have NO fixed pin-peripheral mapping — any GPIO can be routed to any peripheral.",
            "5. Enable peripheral interrupt via NRFX_<PERIPH>_ENABLED=1 in nrfx_config.h.",
            "6. Use nrfx_<periph>_uninit() for clean teardown.",
            "7. EasyDMA peripherals (UARTE, SPIM, TWIM) require buffers in RAM (not flash).",
            "8. SoftDevice (BLE stack) reserves some peripherals — check compatibility.",
        ])

    def get_init_pattern(self, driver: str) -> str:
        return ""

    def get_naming_conventions(self) -> Dict[str, Any]:
        return {
            "function_prefix": "nrfx_<periph>_",
            "config_struct": "nrfx_<periph>_config_t",
            "event_handler": "nrfx_<periph>_event_handler_t",
            "pin_selection": "NRF_GPIO_PIN_MAP(port, pin)",
        }

    def validate_code(self, code: str) -> List[str]:
        return []

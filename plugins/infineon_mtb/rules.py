"""Infineon ModusToolbox architecture rules."""
from __future__ import annotations
from typing import Any, Dict, List
from plugins.base import ArchitectureRulePack

class InfineonArchitectureRules(ArchitectureRulePack):
    def get_rules_text(self) -> str:
        return "\n".join([
            "Infineon ModusToolbox Architecture Rules:",
            "1. Use cyhal_* (HAL) APIs for portable code; Cy_* (PDL) for low-level control.",
            "2. Initialize with cybsp_init() before peripheral configuration.",
            "3. Pin mux configured via Device Configurator — generates cycfg_pins.h.",
            "4. HAL drivers: cyhal_<periph>_init(&obj, pin, ...) — pin passed at init time.",
            "5. Error handling: check cy_rslt_t return (CY_RSLT_SUCCESS).",
            "6. Interrupts: register callbacks via cyhal_<periph>_register_callback().",
            "7. PSoC 6 dual-core: CM0+ handles security/BLE, CM4 runs application.",
            "8. Clock config via HAL or PDL clock APIs — do not write registers directly.",
        ])
    def get_init_pattern(self, driver: str) -> str:
        return ""
    def get_naming_conventions(self) -> Dict[str, Any]:
        return {"function_prefix": "cyhal_<periph>_ (HAL) / Cy_<PERIPH>_ (PDL)",
                "config_struct": "cyhal_<periph>_cfg_t or cy_stc_<periph>_config_t",
                "result_type": "cy_rslt_t"}
    def validate_code(self, code: str) -> List[str]:
        return []

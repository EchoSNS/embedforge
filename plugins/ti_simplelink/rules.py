"""TI SimpleLink architecture rules."""
from __future__ import annotations
from typing import Any, Dict, List
from plugins.base import ArchitectureRulePack

class TIArchitectureRules(ArchitectureRulePack):
    def get_rules_text(self) -> str:
        return "\n".join([
            "TI SimpleLink SDK Architecture Rules:",
            "1. Use TI Drivers API (<ti/drivers/UART2.h>, <ti/drivers/GPIO.h>).",
            "2. Board_init() must be called first — initializes pin mux from ti_drivers_config.c.",
            "3. Driver pattern: handle = <PERIPH>_open(index, &params).",
            "4. Pin configuration via SysConfig tool — generates ti_drivers_config.c/h.",
            "5. Callbacks registered at open time via params struct.",
            "6. TI-RTOS (SYS/BIOS) or FreeRTOS required — use Task, Semaphore, Event.",
            "7. Power management integrated — drivers auto-manage power constraints.",
            "8. Error codes: check NULL handle on open; driver-specific return values.",
        ])
    def get_init_pattern(self, driver: str) -> str:
        return ""
    def get_naming_conventions(self) -> Dict[str, Any]:
        return {"function_prefix": "<PERIPH>_open/close/read/write",
                "params_struct": "<PERIPH>_Params", "handle_type": "<PERIPH>_Handle",
                "config_tool": "SysConfig (.syscfg)"}
    def validate_code(self, code: str) -> List[str]:
        return []

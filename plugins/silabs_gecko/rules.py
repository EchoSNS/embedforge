"""Silicon Labs Gecko SDK architecture rules."""
from __future__ import annotations
from typing import Any, Dict, List
from plugins.base import ArchitectureRulePack

class SiLabsArchitectureRules(ArchitectureRulePack):
    def get_rules_text(self) -> str:
        return "\n".join([
            "Silicon Labs Gecko SDK (emlib) Architecture Rules:",
            "1. Include em_<periph>.h for peripheral access (e.g., em_usart.h, em_gpio.h).",
            "2. Enable clocks via CMU_ClockEnable(cmuClock_<PERIPH>, true) before peripheral init.",
            "3. GPIO routing: configure ROUTELOC/ROUTEPEN registers for peripheral pin mapping.",
            "4. Series 2 (xG2x): use GPIO->*ROUTE registers instead of ROUTELOC.",
            "5. Init structs: use <PERIPH>_INIT_DEFAULT macro then modify fields.",
            "6. Interrupts: enable via NVIC_EnableIRQ() after <PERIPH>_IntEnable().",
            "7. Low-power: use em_emu.h sleep modes; peripherals auto-gate clocks.",
            "8. RAIL (Radio) for wireless — separate from emlib peripheral drivers.",
        ])
    def get_init_pattern(self, driver: str) -> str:
        return ""
    def get_naming_conventions(self) -> Dict[str, Any]:
        return {"function_prefix": "<PERIPH>_Init / <PERIPH>_Enable",
                "init_struct": "<PERIPH>_Init_TypeDef", "clock_enable": "CMU_ClockEnable()"}
    def validate_code(self, code: str) -> List[str]:
        return []

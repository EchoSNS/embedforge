"""AURIX iLLD architecture rules."""
from __future__ import annotations
from typing import Any, Dict, List
from plugins.base import ArchitectureRulePack

class AurixArchitectureRules(ArchitectureRulePack):
    def get_rules_text(self) -> str:
        return "\n".join([
            "Infineon AURIX iLLD Architecture Rules:",
            "1. Include Ifx_Types.h for base types (uint32, boolean, etc.).",
            "2. Driver pattern: IfxModule_Config cfg; IfxModule_initConfig(&cfg); modify; IfxModule_init(&handle, &cfg).",
            "3. Pin selection via IfxPort_setPinMode() or driver-specific pin tables (e.g., IfxAsclin_Tx_P14_0).",
            "4. AURIX has multiple cores — init typically runs on CPU0, assign ISRs to specific cores.",
            "5. Interrupt handling: install ISR via IfxSrc_init(), use IFX_INTERRUPT macro.",
            "6. GTM (Generic Timer Module) drives PWM — configure TOM/ATOM channels.",
            "7. Clock system: use IfxScuCcu for PLL and peripheral clock configuration.",
            "8. Watchdog must be serviced or disabled: IfxScuWdt_disableCpuWatchdog().",
            "9. Error handling: check return values (boolean or IfxModule_Status).",
            "10. Flash programming requires special sequences — use IfxFlash APIs.",
        ])
    def get_init_pattern(self, driver: str) -> str:
        return ""
    def get_naming_conventions(self) -> Dict[str, Any]:
        return {"function_prefix": "Ifx<Module>_", "config_struct": "Ifx<Module>_Config",
                "handle_type": "Ifx<Module>", "pin_table": "Ifx<Module>_<Signal>_P<port>_<pin>"}
    def validate_code(self, code: str) -> List[str]:
        return []

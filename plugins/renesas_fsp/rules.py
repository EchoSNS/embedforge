"""Renesas FSP architecture rules."""
from __future__ import annotations
from typing import Any, Dict, List
from plugins.base import ArchitectureRulePack

class RenesasArchitectureRules(ArchitectureRulePack):
    def get_rules_text(self) -> str:
        return "\n".join([
            "Renesas FSP Architecture Rules:",
            "1. Use FSP API via r_<module>_api_t interface (open, read, write, close).",
            "2. Configure pins via e2studio Pin Configurator — generates r_ioport_cfg.c.",
            "3. Call R_IOPORT_Open() before GPIO usage.",
            "4. Module instances declared via g_<instance>_cfg in generated hal_data.c.",
            "5. Error handling: check fsp_err_t (FSP_SUCCESS, FSP_ERR_*).",
            "6. Interrupts: register callbacks via R_<MODULE>_CallbackSet or config struct.",
            "7. DMA uses r_dtc or r_dmac — link transfer info before starting.",
            "8. Clock config via R_CGC_* APIs or BSP clock init.",
        ])
    def get_init_pattern(self, driver: str) -> str:
        return ""
    def get_naming_conventions(self) -> Dict[str, Any]:
        return {"function_prefix": "R_<MODULE>_", "config_struct": "<module>_cfg_t",
                "instance_struct": "<module>_instance_t", "error_type": "fsp_err_t"}
    def validate_code(self, code: str) -> List[str]:
        return []

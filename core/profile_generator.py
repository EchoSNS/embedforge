"""
Profile Generator — auto-generates capability profiles from SDK header analysis.

Uses the SDKAnalyzer output + LLM to infer peripheral capabilities,
patterns, and constraints from raw function signatures and type definitions.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from core.sdk_analyzer import SDKAnalyzer, SDKAnalysisResult

logger = logging.getLogger(__name__)


class ProfileGenerator:
    """Generates a structured capability profile from an SDK scan."""

    async def generate(
        self,
        sdk_path: str,
        vendor_name: str = "",
        sdk_name: str = "",
    ) -> Dict[str, Any]:
        """Scan SDK and produce a profile dict (YAML-serializable)."""
        logger.info("Generating capability profile from SDK: %s", sdk_path)
        analyzer = SDKAnalyzer(include_paths=[sdk_path])
        scan = analyzer.analyze()
        logger.info("SDK scan complete: %d functions, %d types", len(scan.functions), len(scan.types))

        # Attempt LLM-assisted generation, fall back to heuristic
        try:
            profile = await self._llm_generate(scan, vendor_name, sdk_name)
            logger.info("Profile generated via LLM")
            return profile
        except Exception as e:
            logger.warning("LLM profile generation failed, using heuristics: %s", e)
            return self._heuristic_generate(scan, vendor_name, sdk_name)

    async def _llm_generate(
        self,
        scan: SDKAnalysisResult,
        vendor_name: str,
        sdk_name: str,
    ) -> Dict[str, Any]:
        """Use LLM to infer a structured profile from raw SDK metadata."""
        from config.llm_config import get_llm
        from langchain_core.messages import HumanMessage, SystemMessage

        # Prepare a summary of the SDK for the LLM
        func_summary = "\n".join(
            f"  {f.return_type} {f.name}({f.parameters});"
            for f in scan.functions[:80]
        )
        type_summary = "\n".join(
            f"  {t.kind} {t.name}"
            for t in scan.types[:40]
        )

        system_prompt = (
            "You are an embedded systems SDK analyst. Given a list of C function signatures "
            "and type definitions from an SDK, generate a structured capability profile.\n\n"
            "Output a JSON object with this schema:\n"
            "{\n"
            '  "vendor": "string",\n'
            '  "sdk": "string",\n'
            '  "sdk_version": "string",\n'
            '  "supported_families": ["string"],\n'
            '  "peripherals": {\n'
            '    "PERIPHERAL_TYPE": {\n'
            '      "instances": ["INSTANCE1", "INSTANCE2"],\n'
            '      "features": ["feature1", "feature2"],\n'
            '      "notes": ["usage note"]\n'
            "    }\n"
            "  },\n"
            '  "patterns": {\n'
            '    "init_sequence": ["step1", "step2"],\n'
            '    "naming_conventions": {"key": "value"},\n'
            '    "error_handling": ["rule1"]\n'
            "  },\n"
            '  "constraints": ["constraint1", "constraint2"]\n'
            "}\n\n"
            "Infer peripheral types from function prefixes (e.g., HAL_TIM_PWM → PWM peripheral).\n"
            "Infer instances from type names and macros.\n"
            "Infer features from function capabilities (e.g., DMA variants, interrupt variants)."
        )

        user_prompt = (
            f"SDK Info: vendor={vendor_name or 'unknown'}, name={sdk_name or 'unknown'}\n"
            f"Headers scanned: {scan.headers_scanned}\n"
            f"Functions found: {len(scan.functions)}\n"
            f"Types found: {len(scan.types)}\n\n"
            f"FUNCTION SIGNATURES:\n{func_summary}\n\n"
            f"TYPE DEFINITIONS:\n{type_summary}\n\n"
            "Generate the capability profile JSON."
        )

        llm = get_llm(session_id="system", stage="profile_generation")
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])

        return self._parse_json(response.content)

    def _heuristic_generate(
        self,
        scan: SDKAnalysisResult,
        vendor_name: str,
        sdk_name: str,
    ) -> Dict[str, Any]:
        """Fallback: generate a basic profile from naming pattern heuristics."""
        peripherals: Dict[str, Dict[str, Any]] = {}

        # Group functions by peripheral prefix
        groups: Dict[str, List[str]] = {}
        for fn in scan.functions:
            parts = fn.name.split("_")
            if len(parts) >= 2:
                prefix = f"{parts[0]}_{parts[1]}".upper()
                groups.setdefault(prefix, []).append(fn.name)

        # Map groups to peripheral types
        peripheral_map = {
            "HAL_TIM": "TIMER", "HAL_ADC": "ADC", "HAL_UART": "UART",
            "HAL_USART": "UART", "HAL_SPI": "SPI", "HAL_I2C": "I2C",
            "HAL_GPIO": "GPIO", "HAL_DMA": "DMA", "HAL_CAN": "CAN",
            "HAL_DAC": "DAC", "HAL_RTC": "RTC", "HAL_PWR": "POWER",
        }

        for prefix, funcs in groups.items():
            for map_prefix, periph_type in peripheral_map.items():
                if prefix.startswith(map_prefix):
                    if periph_type not in peripherals:
                        peripherals[periph_type] = {
                            "instances": [],
                            "features": [],
                            "functions_count": 0,
                            "notes": [],
                        }
                    peripherals[periph_type]["functions_count"] += len(funcs)
                    # Detect features from function suffixes
                    for fn_name in funcs:
                        if "_DMA" in fn_name.upper():
                            self._add_unique(peripherals[periph_type]["features"], "dma")
                        if "_IT" in fn_name.upper():
                            self._add_unique(peripherals[periph_type]["features"], "interrupt")
                    break

        # Detect instances from type names
        for t in scan.types:
            if t.kind == "struct" and "HandleTypeDef" in t.name:
                base = t.name.replace("_HandleTypeDef", "")
                for periph_type, data in peripherals.items():
                    if periph_type.lower() in base.lower():
                        self._add_unique(data["instances"], base)

        return {
            "vendor": vendor_name or "Unknown",
            "sdk": sdk_name or "Unknown SDK",
            "sdk_version": "auto-detected",
            "supported_families": [],
            "peripherals": peripherals,
            "patterns": {
                "init_sequence": self._infer_init_sequence(scan),
                "naming_conventions": self._infer_naming(scan),
                "error_handling": [],
            },
            "constraints": [],
        }

    def _infer_init_sequence(self, scan: SDKAnalysisResult) -> List[str]:
        """Infer initialization order from common function names."""
        init_funcs = [f.name for f in scan.functions if "init" in f.name.lower()]
        # Prioritize system-level inits
        order = []
        for pattern in ["HAL_Init", "SystemClock", "RCC", "GPIO_Init", "MX_"]:
            for fn in init_funcs:
                if pattern.lower() in fn.lower() and fn not in order:
                    order.append(fn)
        return order[:10]

    def _infer_naming(self, scan: SDKAnalysisResult) -> Dict[str, str]:
        """Infer naming conventions from function prefixes."""
        conventions = {}
        prefixes = set()
        for fn in scan.functions[:50]:
            parts = fn.name.split("_")
            if parts:
                prefixes.add(parts[0])
        if prefixes:
            conventions["common_prefixes"] = ", ".join(sorted(prefixes)[:5])

        # Detect config struct pattern
        config_types = [t.name for t in scan.types if "Init" in t.name and "TypeDef" in t.name]
        if config_types:
            conventions["config_struct_pattern"] = config_types[0]

        return conventions

    @staticmethod
    def _add_unique(lst: List[str], item: str) -> None:
        if item not in lst:
            lst.append(item)

    @staticmethod
    def _parse_json(text: str) -> Dict[str, Any]:
        """Extract JSON from LLM response."""
        text = text.strip()
        if "```" in text:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                text = text[start:end]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            import re
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            return {"error": "Failed to parse LLM response", "raw": text[:500]}

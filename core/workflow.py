"""
Workflow State Machine — the core multi-stage pipeline.

Implements a human-in-the-loop gated pipeline:
  Clarifier → Refiner → Hardware → SW Architecture → SW Detailed → CodeGen

Each node transforms the state and pauses for human approval before proceeding.
Uses LangGraph StateGraph for execution, but can also run nodes individually.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from config.llm_config import get_llm
from plugins.base import PluginRegistry

logger = logging.getLogger(__name__)


class WorkflowStage(Enum):
    INIT = "init"
    CLARIFIER = "clarifier"
    REFINER = "refiner"
    HARDWARE = "hardware"
    SOFTWARE_ARCH = "software_architecture"
    SOFTWARE_DETAILED = "software_detailed"
    CODEGEN = "codegen"
    REVIEW = "review"
    BUILD = "build"
    COMPLETE = "complete"


@dataclass
class WorkflowState:
    """Immutable-ish state object passed through pipeline stages."""

    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    stage: WorkflowStage = WorkflowStage.INIT
    user_input: str = ""
    board_name: str = ""

    # Stage outputs (JSON-serializable dicts)
    requirements: Dict[str, Any] = field(default_factory=dict)
    hardware_spec: Dict[str, Any] = field(default_factory=dict)
    software_arch: Dict[str, Any] = field(default_factory=dict)
    software_detailed: Dict[str, Any] = field(default_factory=dict)
    generated_code: Dict[str, str] = field(default_factory=dict)
    review_result: Dict[str, Any] = field(default_factory=dict)
    build_result: Dict[str, Any] = field(default_factory=dict)

    # Context
    sdk_capabilities: Dict[str, Any] = field(default_factory=dict)
    reference_analysis: Dict[str, Any] = field(default_factory=dict)
    pin_context: str = ""
    driver_context: str = ""

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now(tz=None).isoformat())
    history: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class WorkflowEngine:
    """
    Executes workflow nodes individually with human-in-the-loop gating.

    Each node:
      1. Reads state
      2. Invokes LLM with dynamically built prompt
      3. Parses structured output
      4. Updates state
      5. Returns for human approval before next node runs
    """

    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry

    def initialize_state(self, user_input: str, board_name: str) -> WorkflowState:
        """Create initial workflow state from user input and board selection."""
        state = WorkflowState(
            user_input=user_input,
            board_name=board_name,
            stage=WorkflowStage.CLARIFIER,
        )

        # Load SDK capabilities from plugin
        try:
            board = self._registry.get_board_template(board_name)
            config = board.get_config()
            state.sdk_capabilities = {
                "mcu": config.mcu,
                "mcu_family": config.mcu_family,
                "clock_hz": config.clock_hz,
                "peripherals": config.peripherals,
            }
        except Exception as e:
            logger.warning(f"Could not load board capabilities: {e}")

        return state

    def run_refiner(self, state: WorkflowState) -> WorkflowState:
        """Refine user requirements into structured JSON spec."""
        from prompts.stages import REFINER_SYSTEM_PROMPT

        profile = self._registry.get_capability_profile()
        profile_context = ""
        if profile:
            peripheral_hint = self._guess_peripheral(state.user_input)
            profile_context = (
                f"\nSDK PROFILE ({profile.sdk} v{profile.sdk_version}):\n"
                f"{profile.get_peripheral_context(peripheral_hint)}\n"
                f"\nCONSTRAINTS:\n{profile.get_constraints_context()}\n"
            )

        user_prompt = (
            f"USER REQUIREMENT:\n{state.user_input}\n\n"
            f"BOARD: {state.board_name}\n"
            f"MCU CAPABILITIES:\n{json.dumps(state.sdk_capabilities, indent=2)}\n"
            f"{profile_context}\n"
            f"Produce a structured requirements JSON matching the output schema."
        )

        result = self._invoke_llm(REFINER_SYSTEM_PROMPT, user_prompt)
        state.requirements = self._parse_json_response(result)
        state.stage = WorkflowStage.HARDWARE
        state.history.append({"stage": "refiner", "timestamp": datetime.utcnow().isoformat()})
        return state

    def run_hardware(self, state: WorkflowState) -> WorkflowState:
        """Assign peripherals and pins based on requirements."""
        from core.mcu_capabilities import MCUCapabilityService
        from prompts.stages import HARDWARE_SYSTEM_PROMPT

        mcu_svc = MCUCapabilityService(self._registry)
        peripheral = state.requirements.get("peripheral_type", "GPIO")
        pin_context = mcu_svc.format_available_pins(peripheral)

        profile = self._registry.get_capability_profile()
        profile_context = ""
        if profile:
            profile_context = (
                f"\nSDK CONSTRAINTS:\n{profile.get_constraints_context()}\n"
                f"\nCLOCK TREE:\n{json.dumps(profile.clock_tree, indent=2)}\n"
            )

        user_prompt = (
            f"REQUIREMENTS:\n{json.dumps(state.requirements, indent=2)}\n\n"
            f"AVAILABLE PINS:\n{pin_context}\n"
            f"{profile_context}\n"
            f"Assign hardware resources following the output schema."
        )

        result = self._invoke_llm(HARDWARE_SYSTEM_PROMPT, user_prompt)
        state.hardware_spec = self._parse_json_response(result)
        state.pin_context = pin_context
        state.stage = WorkflowStage.SOFTWARE_ARCH
        state.history.append({"stage": "hardware", "timestamp": datetime.utcnow().isoformat()})
        return state

    def run_software_arch(self, state: WorkflowState) -> WorkflowState:
        """Select SDK drivers and define architecture."""
        from core.driver_catalog import DriverCatalogService
        from prompts.stages import SOFTWARE_ARCH_SYSTEM_PROMPT

        catalog_svc = DriverCatalogService(self._registry)
        peripheral = state.requirements.get("peripheral_type", "GPIO")
        driver_options = catalog_svc.format_peripheral_summary(peripheral)

        user_prompt = (
            f"REQUIREMENTS:\n{json.dumps(state.requirements, indent=2)}\n\n"
            f"HARDWARE SPEC:\n{json.dumps(state.hardware_spec, indent=2)}\n\n"
            f"AVAILABLE DRIVERS:\n{driver_options}\n\n"
            f"Select drivers and define architecture following the output schema."
        )

        result = self._invoke_llm(SOFTWARE_ARCH_SYSTEM_PROMPT, user_prompt)
        state.software_arch = self._parse_json_response(result)
        state.driver_context = driver_options
        state.stage = WorkflowStage.SOFTWARE_DETAILED
        state.history.append({"stage": "software_arch", "timestamp": datetime.utcnow().isoformat()})
        return state

    def run_software_detailed(self, state: WorkflowState) -> WorkflowState:
        """Generate detailed function-level design."""
        from prompts.stages import SOFTWARE_DETAILED_SYSTEM_PROMPT

        rules = self._registry.get_architecture_rules()
        rules_text = rules.get_rules_text()

        profile = self._registry.get_capability_profile()
        patterns_context = ""
        if profile:
            patterns_context = f"\nSDK PATTERNS:\n{profile.get_patterns_context()}\n"

        user_prompt = (
            f"REQUIREMENTS:\n{json.dumps(state.requirements, indent=2)}\n\n"
            f"ARCHITECTURE:\n{json.dumps(state.software_arch, indent=2)}\n\n"
            f"HARDWARE:\n{json.dumps(state.hardware_spec, indent=2)}\n\n"
            f"SDK DRIVERS:\n{state.driver_context}\n\n"
            f"PIN ASSIGNMENTS:\n{state.pin_context}\n\n"
            f"ARCHITECTURE RULES:\n{rules_text}\n"
            f"{patterns_context}\n"
            f"Create detailed design following the output schema."
        )

        result = self._invoke_llm(SOFTWARE_DETAILED_SYSTEM_PROMPT, user_prompt)
        state.software_detailed = self._parse_json_response(result)
        state.stage = WorkflowStage.CODEGEN
        state.history.append({"stage": "software_detailed", "timestamp": datetime.utcnow().isoformat()})
        return state

    def run_codegen(self, state: WorkflowState) -> WorkflowState:
        """Generate production code using TDD pipeline."""
        from core.tdd_generator import TDDGenerator

        rules = self._registry.get_architecture_rules()
        generator = TDDGenerator(self._registry)

        # Inject reference snippet from capability profile if available
        reference_context = ""
        profile = self._registry.get_capability_profile()
        if profile:
            peripheral = state.requirements.get("peripheral_type", "")
            snippet = profile.get_reference_snippet(peripheral)
            if snippet:
                reference_context = f"REFERENCE EXAMPLE:\n```c\n{snippet}\n```"

        if state.reference_analysis:
            reference_context += f"\n\n{json.dumps(state.reference_analysis)}"

        result = generator.generate(
            requirements=state.software_detailed or state.requirements,
            driver_context=state.driver_context,
            pin_context=state.pin_context,
            architecture_rules=rules.get_rules_text(),
            reference_context=reference_context,
        )

        if result.success:
            state.generated_code = {
                **result.mock_files,
                **result.test_files,
                **result.production_files,
            }
        else:
            state.errors.extend(result.errors)

        state.stage = WorkflowStage.REVIEW
        state.history.append({"stage": "codegen", "timestamp": datetime.utcnow().isoformat()})
        return state

    def run_review(self, state: WorkflowState) -> WorkflowState:
        """AI-review the generated code."""
        from core.ai_reviewer import AIReviewer

        reviewer = AIReviewer(self._registry)
        result = reviewer.review(
            files=state.generated_code,
            requirements=state.user_input,
        )

        state.review_result = {
            "verdict": result.verdict,
            "score": result.score,
            "summary": result.summary,
            "issues": [
                {"severity": i.severity, "location": i.location, "message": i.message}
                for i in result.issues
            ],
        }
        state.stage = WorkflowStage.BUILD
        state.history.append({"stage": "review", "timestamp": datetime.utcnow().isoformat()})
        return state

    def _invoke_llm(self, system_prompt: str, user_prompt: str) -> str:
        from server.activity_log import activity_log
        import time

        activity_log.ai("Sending prompt to LLM…", f"System: {system_prompt[:80]}…")
        t0 = time.time()

        llm = get_llm(temperature=0.1, max_tokens=6000)
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])

        elapsed = time.time() - t0
        content = response.content
        activity_log.ai(f"LLM responded in {elapsed:.1f}s", f"{len(content)} chars")
        return content

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Extract JSON from LLM response, handling markdown code fences."""
        text = response.strip()

        # Strip markdown code fences
        if "```" in text:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                text = text[start:end]

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in the response
            import re
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass

            logger.warning("Failed to parse JSON from LLM response")
            return {"raw_response": response[:2000]}

    @staticmethod
    def _guess_peripheral(user_input: str) -> str:
        """Heuristic to detect primary peripheral type from natural language."""
        text = user_input.upper()
        keywords = {
            "PWM": ["PWM", "DUTY", "DEAD-TIME", "COMPLEMENTARY", "BLDC", "MOTOR"],
            "ADC": ["ADC", "ANALOG", "SAMPLE", "CONVERSION"],
            "UART": ["UART", "USART", "SERIAL", "BAUD", "RS232", "RS485"],
            "SPI": ["SPI", "MOSI", "MISO", "SCLK"],
            "I2C": ["I2C", "SCL", "SDA", "SLAVE", "MASTER"],
            "TIMER": ["TIMER", "TIM", "BLINK", "DELAY", "FREQUENCY"],
            "CAN": ["CAN", "CANBUS", "CAN-BUS"],
            "GPIO": ["GPIO", "LED", "BUTTON", "PIN"],
        }
        for peripheral, kws in keywords.items():
            if any(kw in text for kw in kws):
                return peripheral
        return "GPIO"

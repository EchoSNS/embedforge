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
from core.schemas import HardwareSpec, RefinedRequirements, SoftwareArchitecture, SoftwareDetailed
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
        self._current_session_id = "unknown"

    def initialize_state(self, user_input: str, board_name: str) -> WorkflowState:
        """Create initial workflow state from user input and board selection."""
        from core.prompt_guard import sanitize_user_input, detect_injection

        detections = detect_injection(user_input)
        if detections:
            logger.warning("Prompt injection attempt detected in user input: %s", [d[0] for d in detections])

        sanitized_input = sanitize_user_input(user_input)
        logger.info("Initializing workflow state: board=%s, input=%s", board_name, sanitized_input[:80])
        state = WorkflowState(
            user_input=sanitized_input,
            board_name=board_name,
            stage=WorkflowStage.CLARIFIER,
        )
        self._current_session_id = state.session_id

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
            logger.info("Loaded board capabilities: MCU=%s, family=%s", config.mcu, config.mcu_family)
        except Exception as e:
            logger.warning("Could not load board capabilities: %s", e)

        return state

    def run_refiner(self, state: WorkflowState) -> WorkflowState:
        """Refine user requirements into structured JSON spec."""
        logger.info("Running refiner stage for session %s", state.session_id)
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

        result = self._invoke_llm_structured(REFINER_SYSTEM_PROMPT, user_prompt, RefinedRequirements, stage="refiner")
        state.requirements = result
        state.stage = WorkflowStage.HARDWARE
        state.history.append({"stage": "refiner", "timestamp": datetime.utcnow().isoformat()})
        return state

    def run_hardware(self, state: WorkflowState) -> WorkflowState:
        """Assign peripherals and pins based on requirements."""
        logger.info("Running hardware stage for session %s", state.session_id)
        from core.mcu_capabilities import MCUCapabilityService
        from prompts.stages import HARDWARE_SYSTEM_PROMPT

        mcu_svc = MCUCapabilityService(self._registry)
        peripheral = state.requirements.get("peripheral_type", "GPIO")
        pin_context = mcu_svc.format_available_pins(peripheral)

        # Enrich pin context with device DB ground truth if available
        device_pin_context = self._get_device_db_pin_context(peripheral)
        if device_pin_context:
            pin_context = device_pin_context

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

        result = self._invoke_llm_structured(HARDWARE_SYSTEM_PROMPT, user_prompt, HardwareSpec, stage="hardware")
        state.hardware_spec = result
        state.hardware_spec = self._validate_hardware_output(state.hardware_spec, state.requirements)
        state.pin_context = pin_context
        state.stage = WorkflowStage.SOFTWARE_ARCH
        state.history.append({"stage": "hardware", "timestamp": datetime.utcnow().isoformat()})
        return state

    def run_software_arch(self, state: WorkflowState) -> WorkflowState:
        """Select SDK drivers and define architecture."""
        logger.info("Running software architecture stage for session %s", state.session_id)
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

        result = self._invoke_llm_structured(SOFTWARE_ARCH_SYSTEM_PROMPT, user_prompt, SoftwareArchitecture, stage="software_arch")
        state.software_arch = result
        state.driver_context = driver_options
        state.stage = WorkflowStage.SOFTWARE_DETAILED
        state.history.append({"stage": "software_arch", "timestamp": datetime.utcnow().isoformat()})
        return state

    def run_software_detailed(self, state: WorkflowState) -> WorkflowState:
        """Generate detailed function-level design."""
        logger.info("Running detailed design stage for session %s", state.session_id)
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

        result = self._invoke_llm_structured(SOFTWARE_DETAILED_SYSTEM_PROMPT, user_prompt, SoftwareDetailed, stage="software_detailed")
        state.software_detailed = result
        state.stage = WorkflowStage.CODEGEN
        state.history.append({"stage": "software_detailed", "timestamp": datetime.utcnow().isoformat()})
        return state

    def run_codegen(self, state: WorkflowState) -> WorkflowState:
        """Generate production code using TDD pipeline."""
        logger.info("Running code generation stage for session %s", state.session_id)
        from core.tdd_generator import TDDGenerator
        from server.activity_log import activity_log

        phase_labels = {
            "mock_generation": "Mock Generation (Phase 1/3)",
            "test_generation": "Test Generation (Phase 2/3)",
            "production_code": "Production Code (Phase 3/3)",
        }

        def _on_tdd_progress(phase: str, detail: str) -> None:
            label = phase_labels.get(phase, phase)
            activity_log.ai(f"TDD — {label}", detail)

        rules = self._registry.get_architecture_rules()
        generator = TDDGenerator(self._registry, session_id=self._current_session_id)

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
            on_progress=_on_tdd_progress,
        )

        if result.success:
            state.generated_code = {
                **result.mock_files,
                **result.test_files,
                **result.production_files,
            }
            state.stage = WorkflowStage.REVIEW
        else:
            state.errors.extend(result.errors)
            if result.error_detail:
                logger.error("Codegen failed at phase %s: %s", result.phase.value, result.error_detail)

        state.history.append({"stage": "codegen", "timestamp": datetime.utcnow().isoformat()})
        return state

    def run_review(self, state: WorkflowState) -> WorkflowState:
        """Run deterministic validation first, then AI review for semantic checks."""
        logger.info("Running review stage for session %s", state.session_id)
        from core.ai_reviewer import AIReviewer
        from core.code_validator import CodeValidator

        # Phase 1: Deterministic validation (pins, includes, rules, syntax)
        validator = CodeValidator(self._registry)
        validation = validator.validate(state.generated_code)

        deterministic_issues = []
        for err in validation.errors:
            deterministic_issues.append({"severity": "error", "location": "", "message": err})
        for pin_issue in validation.pin_issues:
            deterministic_issues.append({"severity": "error", "location": "", "message": pin_issue})
        for hdr in validation.missing_headers:
            deterministic_issues.append({"severity": "warning", "location": "", "message": hdr})
        for rule in validation.rule_violations:
            deterministic_issues.append({"severity": "warning", "location": "", "message": rule})

        if not validation.passed:
            state.review_result = {
                "verdict": "needs_fixes",
                "score": max(0, 50 - len(deterministic_issues) * 10),
                "summary": f"Deterministic validation failed: {len(deterministic_issues)} issues found before AI review.",
                "issues": deterministic_issues,
            }
            state.stage = WorkflowStage.BUILD
            state.history.append({"stage": "review", "timestamp": datetime.utcnow().isoformat()})
            return state

        # Phase 2: AI review for semantic correctness (only if deterministic checks pass)
        reviewer = AIReviewer(self._registry, session_id=self._current_session_id)
        result = reviewer.review(
            files=state.generated_code,
            requirements=state.user_input,
        )

        all_issues = deterministic_issues + [
            {"severity": i.severity, "location": i.location, "message": i.message}
            for i in result.issues
        ]

        state.review_result = {
            "verdict": result.verdict,
            "score": result.score,
            "summary": result.summary,
            "issues": all_issues,
        }
        state.stage = WorkflowStage.BUILD
        state.history.append({"stage": "review", "timestamp": datetime.utcnow().isoformat()})
        return state

    def _invoke_llm(self, system_prompt: str, user_prompt: str, stage: str = "unknown") -> str:
        from server.activity_log import activity_log
        from core.llm_cache import llm_cache
        import time

        # Check cache first (skips LLM call + cost if hit)
        cached = llm_cache.get(system_prompt, user_prompt)
        if cached is not None:
            activity_log.ai("Cache HIT — skipping LLM call", f"Stage: {stage}")
            return cached

        activity_log.ai("Sending prompt to LLM…", f"System: {system_prompt[:80]}…")
        t0 = time.time()

        llm = get_llm(session_id=self._current_session_id, stage=stage)
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])

        elapsed = time.time() - t0
        content = response.content
        activity_log.ai(f"LLM responded in {elapsed:.1f}s", f"{len(content)} chars")

        llm_cache.put(system_prompt, user_prompt, content)
        return content

    def _invoke_llm_structured(self, system_prompt: str, user_prompt: str, schema, stage: str = "unknown") -> Dict[str, Any]:
        """Invoke LLM with structured output enforcement via Pydantic schema."""
        from server.activity_log import activity_log
        import time

        activity_log.ai("Sending structured prompt to LLM…", f"Stage: {stage}")
        t0 = time.time()

        llm = get_llm(session_id=self._current_session_id, stage=stage)

        try:
            structured_llm = llm.with_structured_output(schema)
            result = structured_llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ])
            elapsed = time.time() - t0
            activity_log.ai(f"Structured response in {elapsed:.1f}s", f"Schema: {schema.__name__}")
            return result.model_dump() if hasattr(result, "model_dump") else dict(result)
        except Exception as e:
            logger.warning("Structured output failed (%s), falling back to raw parse: %s", schema.__name__, e)
            raw = self._invoke_llm(system_prompt, user_prompt, stage=stage)
            return self._parse_json_response(raw)

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

            logger.warning("Failed to parse JSON from LLM response (len=%d)", len(response))
            return {"raw_response": response[:2000]}

    @staticmethod
    def _validate_hardware_output(
        hardware_spec: Dict[str, Any], requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Ensure hardware stage output has complete pin_assignments.

        Cross-references peripherals with pin_assignments and repairs
        missing entries by extracting pin info from peripheral descriptions.
        """
        import re

        peripherals = hardware_spec.get("peripherals", [])
        pin_assignments = hardware_spec.get("pin_assignments", {})
        if pin_assignments is None:
            pin_assignments = {}

        if not pin_assignments and peripherals:
            # Extract pin info from peripheral roles/descriptions
            pin_pattern = re.compile(r"P[A-K]\d{1,2}", re.IGNORECASE)
            channel_pattern = re.compile(r"([\w]+_CH\d+|[\w]+_TX|[\w]+_RX|[\w]+_SCK|[\w]+_MOSI|[\w]+_MISO|[\w]+_SDA|[\w]+_SCL)", re.IGNORECASE)

            for periph in peripherals:
                role = periph.get("role", "")
                instance = periph.get("instance", "")

                # Find pin references in role text
                pins_found = pin_pattern.findall(role)
                channels_found = channel_pattern.findall(role)

                if pins_found:
                    pin = pins_found[0].upper()
                    if channels_found:
                        key = channels_found[0].upper()
                    else:
                        key = f"{instance}_OUT" if instance else periph.get("type", "GPIO")
                    pin_assignments[key] = pin

            # Also check requirements features for pin info
            features = requirements.get("features", [])
            for feat in features:
                if isinstance(feat, str):
                    pins = pin_pattern.findall(feat)
                    channels = channel_pattern.findall(feat)
                    if pins and channels:
                        pin_assignments.setdefault(channels[0].upper(), pins[0].upper())

        hardware_spec["pin_assignments"] = pin_assignments
        return hardware_spec

    @staticmethod
    def _get_device_db_pin_context(peripheral_type: str) -> str:
        """Query device DB for complete pin-AF mapping if available."""
        try:
            from core.device_db import get_device_db
            db = get_device_db()
            if not db.has_device_data():
                return ""
            devices = db.list_devices()
            if not devices:
                return ""
            device_id = db.find_device(devices[0]["device"])
            if device_id is None:
                return ""
            entries = db.get_pin_mux(device_id, peripheral_type)
            if not entries:
                return ""
            lines = [f"DEVICE PIN-MUX TABLE ({devices[0]['device']}) — {peripheral_type} pins:"]
            for e in entries[:60]:
                af_str = f"AF{e.af_number}" if e.af_number >= 0 else ""
                lines.append(f"  {e.pin_name} → {e.signal} ({af_str}) [{e.peripheral}]")
            if len(entries) > 60:
                lines.append(f"  ... and {len(entries) - 60} more")
            return "\n".join(lines)
        except Exception:
            return ""

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

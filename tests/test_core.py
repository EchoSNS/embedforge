"""Tests for core services."""

import pytest

from plugins.base import PluginRegistry
from plugins.stm32_hal import register

from core.driver_catalog import DriverCatalogService
from core.driver_selector import DriverSelector, SelectionCriteria
from core.mcu_capabilities import MCUCapabilityService
from core.architecture_rules import ArchitectureRulesService
from core.pin_validator import PinValidator
from core.reference_analyzer import ReferenceProjectAnalyzer


@pytest.fixture
def registry():
    reg = PluginRegistry()
    register(reg)
    reg.activate("stm32_hal")
    return reg


def test_driver_catalog_service(registry):
    svc = DriverCatalogService(registry)
    peripherals = svc.list_peripherals()
    assert "PWM" in peripherals

    context = svc.get_driver_context("HAL_TIM_PWM")
    assert "HAL_TIM_PWM" in context
    assert "PWM" in context


def test_driver_selector(registry):
    selector = DriverSelector(registry)

    result = selector.select(SelectionCriteria(
        peripheral="PWM",
        channel_count=3,
        needs_complementary=True,
        needs_dead_time=True,
    ))

    assert result is not None
    assert result.driver.name == "HAL_TIM_PWM_N"
    assert result.score > 0
    assert result.rationale


def test_mcu_capability_service(registry):
    svc = MCUCapabilityService(registry)
    assert svc.validate_pin("PA8")
    assert not svc.validate_pin("INVALID_PIN")

    formatted = svc.format_available_pins("PWM")
    assert "PA8" in formatted


def test_architecture_rules_service(registry):
    svc = ArchitectureRulesService(registry)
    rules = svc.get_rules_for_prompt()
    assert "HAL" in rules
    assert len(rules) > 100


def test_pin_validator(registry):
    validator = PinValidator(registry)

    code_with_valid_pin = "HAL_GPIO_Init(GPIOA, &GPIO_InitStruct); // PA5"
    # Note: pin patterns match PA5 etc. in pin_patterns from plugin
    # The actual validation depends on the regex matching pin symbol strings


def test_reference_analyzer():
    analyzer = ReferenceProjectAnalyzer()

    files = {
        "main.c": """
#include "stm32f4xx_hal.h"
#include "main.h"

TIM_HandleTypeDef htim1;

void MX_TIM1_Init(void) {
    htim1.Instance = TIM1;
    HAL_TIM_PWM_Init(&htim1);
    HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);
}

int main(void) {
    HAL_Init();
    MX_TIM1_Init();
    while(1) {}
}
""",
        "main.h": """
#ifndef MAIN_H
#define MAIN_H
void MX_TIM1_Init(void);
#endif
""",
    }

    result = analyzer.analyze_files(files)
    assert result.files_analyzed == 2
    assert "stm32f4xx_hal.h" in result.includes
    assert any(f.name == "MX_TIM1_Init" for f in result.functions_defined)
    assert "HAL_TIM_PWM_Init" in result.functions_called
    assert result.patterns.get("has_init_pattern")


def test_cost_tracker():
    import tempfile
    from pathlib import Path
    import core.cost_tracker as ct
    ct._COST_DB_PATH = Path(tempfile.mktemp(suffix=".db"))
    from core.cost_tracker import CostTracker

    tracker = CostTracker()

    record = tracker.record_call(
        session_id="test-session",
        stage="refiner",
        model="gpt-4o",
        input_tokens=1500,
        output_tokens=500,
        duration_ms=1200.0,
    )

    assert record.cost_usd > 0
    assert record.total_tokens == 2000

    tracker.record_call(
        session_id="test-session",
        stage="hardware",
        model="gpt-4o",
        input_tokens=2000,
        output_tokens=800,
        duration_ms=1500.0,
    )

    summary = tracker.get_session_summary("test-session")
    assert summary["call_count"] == 2
    assert summary["total_input_tokens"] == 3500
    assert summary["total_cost_usd"] > 0
    assert "refiner" in summary["by_stage"]
    assert "hardware" in summary["by_stage"]

    global_summary = tracker.get_global_summary()
    assert global_summary["total_calls"] == 2
    assert global_summary["session_count"] == 1


def test_schemas():
    from core.schemas import RefinedRequirements, HardwareSpec

    req = RefinedRequirements(
        peripheral_type="PWM",
        channel_count=3,
        features=["complementary", "dead_time"],
        description="3-phase PWM for BLDC motor",
    )
    assert req.peripheral_type == "PWM"
    assert req.model_dump()["channel_count"] == 3

    hw = HardwareSpec(
        pin_assignments={"CH1": "PA8", "CH1N": "PB13"},
    )
    assert hw.pin_assignments["CH1"] == "PA8"

"""Tests for remaining Phase 2 features: tree-sitter, rollback, RAG integration."""

import pytest


def test_tree_sitter_parser_functions():
    from core.ts_parser import parse_header
    from core.sdk_analyzer import SDKAnalysisResult

    code = b"""
typedef struct {
    uint32_t Prescaler;
    uint32_t CounterMode;
} TIM_Base_InitTypeDef;

typedef enum {
    HAL_OK = 0,
    HAL_ERROR = 1,
    HAL_BUSY = 2,
} HAL_StatusTypeDef;

HAL_StatusTypeDef HAL_TIM_PWM_Init(TIM_HandleTypeDef *htim);
void HAL_GPIO_WritePin(GPIO_TypeDef *GPIOx, uint16_t Pin, GPIO_PinState State);
uint32_t HAL_GetTick(void);

#define TIM_CHANNEL_1  0x00000000U
#define GPIO_PIN_5     ((uint16_t)0x0020)
"""
    result = SDKAnalysisResult()
    parse_header(code, "test.h", result)

    assert result.headers_scanned == 1
    func_names = [f.name for f in result.functions]
    assert "HAL_TIM_PWM_Init" in func_names
    assert "HAL_GPIO_WritePin" in func_names
    assert "HAL_GetTick" in func_names

    type_names = [t.name for t in result.types]
    assert "TIM_Base_InitTypeDef" in type_names
    assert "HAL_StatusTypeDef" in type_names

    assert "TIM_CHANNEL_1" in result.macros
    assert "GPIO_PIN_5" in result.macros


def test_tree_sitter_handles_ifdef():
    from core.ts_parser import parse_header
    from core.sdk_analyzer import SDKAnalysisResult

    code = b"""
#ifdef HAL_TIM_MODULE_ENABLED
HAL_StatusTypeDef HAL_TIM_Base_Init(TIM_HandleTypeDef *htim);
HAL_StatusTypeDef HAL_TIM_Base_Start(TIM_HandleTypeDef *htim);
#endif
"""
    result = SDKAnalysisResult()
    parse_header(code, "guarded.h", result)

    func_names = [f.name for f in result.functions]
    assert "HAL_TIM_Base_Init" in func_names
    assert "HAL_TIM_Base_Start" in func_names


def test_sdk_analyzer_uses_tree_sitter():
    """Verify SDKAnalyzer._parse_header uses tree-sitter when available."""
    from core.sdk_analyzer import SDKAnalyzer, SDKAnalysisResult
    import tempfile
    from pathlib import Path

    code = "HAL_StatusTypeDef HAL_UART_Init(UART_HandleTypeDef *huart);\n"
    with tempfile.NamedTemporaryFile(suffix=".h", mode="w", delete=False, encoding="utf-8") as f:
        f.write(code)
        f.flush()
        analyzer = SDKAnalyzer()
        result = SDKAnalysisResult()
        analyzer._parse_header(Path(f.name), result)

    assert any(f.name == "HAL_UART_Init" for f in result.functions)


def test_workflow_state_rollback():
    from core.workflow import WorkflowState, WorkflowStage

    state = WorkflowState(stage=WorkflowStage.SOFTWARE_DETAILED)
    state.requirements = {"peripheral_type": "PWM"}
    state.hardware_spec = {"pin": "PA8"}
    state.software_arch = {"driver": "HAL_TIM"}
    state.software_detailed = {"functions": []}

    state.save_snapshot()

    assert state.rollback_to("hardware")
    assert state.stage == WorkflowStage.HARDWARE
    assert state.software_arch == {}
    assert state.software_detailed == {}
    assert state.requirements == {"peripheral_type": "PWM"}
    assert len(state.errors) == 0


def test_workflow_state_rollback_invalid():
    from core.workflow import WorkflowState, WorkflowStage

    state = WorkflowState(stage=WorkflowStage.HARDWARE)
    assert state.rollback_to("codegen") is False  # can't go forward
    assert state.rollback_to("nonexistent") is False


def test_stage_models_api():
    from config.settings import get_stage_models, set_stage_models

    original = get_stage_models()
    set_stage_models({"refiner": "gpt-4o-mini", "chat": "gpt-4o-mini"})
    assert get_stage_models()["refiner"] == "gpt-4o-mini"

    set_stage_models({})
    assert get_stage_models() == {}

    # Reset
    import config.settings as cs
    cs._runtime_stage_models = None

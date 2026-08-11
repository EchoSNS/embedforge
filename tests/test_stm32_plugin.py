"""Tests for the plugin interface and STM32 HAL plugin."""

import pytest

from plugins.base import PluginRegistry
from plugins.stm32_hal import MANIFEST, register


@pytest.fixture
def registry():
    reg = PluginRegistry()
    register(reg)
    reg.activate("stm32_hal")
    return reg


def test_plugin_registration(registry):
    assert registry.active is not None
    assert registry.active.name == "stm32_hal"


def test_driver_catalog_list_peripherals(registry):
    catalog = registry.get_driver_catalog()
    peripherals = catalog.list_peripherals()
    assert "PWM" in peripherals
    assert "GPIO" in peripherals
    assert "ADC" in peripherals
    assert "UART" in peripherals


def test_driver_catalog_list_drivers(registry):
    catalog = registry.get_driver_catalog()
    pwm_drivers = catalog.list_drivers("PWM")
    assert len(pwm_drivers) >= 2
    names = [d.name for d in pwm_drivers]
    assert "HAL_TIM_PWM" in names
    assert "HAL_TIM_PWM_N" in names


def test_driver_catalog_recommend(registry):
    catalog = registry.get_driver_catalog()

    # Simple PWM → HAL_TIM_PWM
    simple = catalog.recommend_driver("PWM", {"channel_count": 1})
    assert simple is not None
    assert simple.name == "HAL_TIM_PWM"

    # Complementary PWM → HAL_TIM_PWM_N
    complex_ = catalog.recommend_driver("PWM", {"needs_complementary": True})
    assert complex_ is not None
    assert complex_.name == "HAL_TIM_PWM_N"


def test_driver_catalog_functions(registry):
    catalog = registry.get_driver_catalog()
    funcs = catalog.get_driver_functions("HAL_GPIO")
    assert len(funcs) >= 3
    names = [f["name"] for f in funcs]
    assert "HAL_GPIO_Init" in names


def test_pin_provider_validate(registry):
    pins = registry.get_pin_provider()
    assert pins.validate_pin("PA5")
    assert pins.validate_pin("PB13")
    assert not pins.validate_pin("PZ99")


def test_pin_provider_available_pins(registry):
    pins = registry.get_pin_provider()
    pwm_pins = pins.get_available_pins("PWM")
    assert len(pwm_pins) > 0
    assert all(p.peripheral == "PWM" for p in pwm_pins)


def test_pin_provider_conflict_detection(registry):
    pins = registry.get_pin_provider()
    # Same pin used twice → conflict
    errors = pins.validate_assignment({"func_a": "PA8", "func_b": "PA8"})
    assert len(errors) == 1
    assert "conflict" in errors[0].lower()


def test_compiler_info(registry):
    compiler = registry.get_compiler()
    info = compiler.get_info()
    assert "available" in info


def test_architecture_rules(registry):
    rules = registry.get_architecture_rules()
    text = rules.get_rules_text()
    assert "HAL" in text
    assert len(text) > 100

    conventions = rules.get_naming_conventions()
    assert "handle_prefix" in conventions


def test_architecture_rules_validation(registry):
    rules = registry.get_architecture_rules()

    # Code without clock enable
    bad_code = """
    TIM_HandleTypeDef htim1;
    HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);
    """
    violations = rules.validate_code(bad_code)
    assert len(violations) > 0


def test_board_template(registry):
    board = registry.get_board_template("NUCLEO-F446RE")
    config = board.get_config()

    assert config.name == "NUCLEO-F446RE"
    assert config.mcu == "STM32F446RET6"
    assert config.clock_hz == 180_000_000
    assert "TIM1" in config.peripherals

    templates = board.get_template_files()
    assert "main.c" in templates
    assert "int main" in templates["main.c"]


def test_board_list(registry):
    boards = registry.list_boards()
    assert "NUCLEO-F446RE" in boards

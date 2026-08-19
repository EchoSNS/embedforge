"""ESP-IDF architecture rules."""

from __future__ import annotations

from typing import Any, Dict, List

from plugins.base import ArchitectureRulePack


class ESPArchitectureRules(ArchitectureRulePack):
    def get_rules_text(self) -> str:
        return "\n".join([
            "Espressif ESP-IDF Architecture Rules:",
            "1. Use ESP-IDF component drivers (driver/, esp_adc/, esp_timer/).",
            "2. Include <driver/uart.h>, <driver/gpio.h>, etc. — not raw register headers.",
            "3. Configuration uses *_config_t structs with designated initializers.",
            "4. Error handling: check esp_err_t returns (ESP_OK, ESP_FAIL, ESP_ERR_*).",
            "5. Use ESP_ERROR_CHECK() for non-recoverable errors during init.",
            "6. GPIO matrix allows any function on any GPIO — use gpio_set_direction + gpio_matrix_out/in.",
            "7. FreeRTOS is mandatory — use tasks, queues, semaphores for concurrency.",
            "8. ISR handlers must be in IRAM (IRAM_ATTR attribute).",
            "9. DMA buffers must be in internal RAM (not PSRAM) unless configured.",
            "10. Use ESP_LOG* macros for debug output, not printf.",
        ])

    def get_init_pattern(self, driver: str) -> str:
        return ""

    def get_naming_conventions(self) -> Dict[str, Any]:
        return {
            "function_prefix": "<component>_<action> (e.g., uart_driver_install)",
            "config_struct": "<periph>_config_t",
            "error_type": "esp_err_t",
            "isr_attribute": "IRAM_ATTR",
            "logging": "ESP_LOGI/W/E(TAG, ...)",
        }

    def validate_code(self, code: str) -> List[str]:
        return []

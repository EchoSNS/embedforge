"""NXP compiler backend — reuses ARM GCC (same toolchain as STM32)."""

from plugins.stm32_hal.compiler import ARMGCCCompiler

# NXP Cortex-M uses the same arm-none-eabi-gcc toolchain
ARMGCCCompiler = ARMGCCCompiler

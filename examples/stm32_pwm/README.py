"""Example: 3-Phase PWM for Motor Control on Nucleo-F446RE

Input requirement for EmbedForge:
  "3-phase complementary PWM at 20kHz with 1µs dead-time using TIM1 for BLDC motor control"

This is a complex example demonstrating:
- Advanced timer (TIM1) with complementary outputs
- Dead-time generation
- Multiple channels synchronized
- HAL_TIMEx_PWMN_Start usage
"""

REQUIREMENT = (
    "Generate a 3-phase complementary PWM driver at 20kHz using TIM1 "
    "with 1 microsecond dead-time for BLDC motor control. "
    "Use channels 1, 2, 3 with complementary outputs on CH1N, CH2N, CH3N."
)
BOARD = "NUCLEO-F446RE"

"""
Stage Output Schemas — Pydantic models for each workflow stage's LLM output.

Used with LangChain's with_structured_output() to enforce valid JSON
from the LLM instead of fragile regex parsing.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RefinedRequirements(BaseModel):
    """Output of the Refiner stage."""

    peripheral_type: str = Field(description="Primary peripheral type: PWM, ADC, UART, SPI, I2C, GPIO, TIMER, CAN")
    channel_count: int = Field(default=1, description="Number of channels/instances needed")
    frequency_hz: Optional[int] = Field(default=None, description="Target frequency in Hz")
    duty_cycle_percent: Optional[float] = Field(default=None, description="Duty cycle percentage")
    features: List[str] = Field(default_factory=list, description="Required features")
    constraints: List[str] = Field(default_factory=list, description="Hardware/software constraints")
    interrupt_required: bool = Field(default=False)
    dma_required: bool = Field(default=False)
    description: str = Field(description="Refined requirement description")


class PeripheralAssignment(BaseModel):
    type: str
    instance: str
    role: str


class ClockConfig(BaseModel):
    source: str = ""
    prescaler: int = 1
    frequency_hz: int = 0


class InterruptConfig(BaseModel):
    source: str
    priority: int = 0
    handler: str = ""


class HardwareSpec(BaseModel):
    """Output of the Hardware stage."""

    peripherals: List[PeripheralAssignment] = Field(default_factory=list)
    pin_assignments: Dict[str, str] = Field(default_factory=dict)
    clock_config: ClockConfig = Field(default_factory=ClockConfig)
    interrupts: List[InterruptConfig] = Field(default_factory=list)


class DriverSelection(BaseModel):
    name: str
    role: str = ""
    api_layer: str = ""
    rationale: str = ""


class SoftwareArchitecture(BaseModel):
    """Output of the Software Architecture stage."""

    selected_drivers: List[DriverSelection] = Field(default_factory=list)
    init_order: List[str] = Field(default_factory=list)
    dependencies: Dict[str, List[str]] = Field(default_factory=dict)
    file_structure: Dict[str, str] = Field(default_factory=dict)
    rationale: str = ""


class FunctionDesign(BaseModel):
    name: str
    signature: str = ""
    description: str = ""
    calls: List[str] = Field(default_factory=list)
    file: str = ""


class ISRDefinition(BaseModel):
    name: str
    vector: str = ""
    priority: int = 0
    actions: List[str] = Field(default_factory=list)


class ConfigField(BaseModel):
    name: str
    type: str = ""
    value: str = ""


class ConfigStruct(BaseModel):
    name: str
    fields: List[ConfigField] = Field(default_factory=list)


class SoftwareDetailed(BaseModel):
    """Output of the Software Detailed Design stage."""

    functions: List[FunctionDesign] = Field(default_factory=list)
    isr_definitions: List[ISRDefinition] = Field(default_factory=list)
    config_structs: List[ConfigStruct] = Field(default_factory=list)
    file_layout: Dict[str, List[str]] = Field(default_factory=dict)


class ReviewIssueSchema(BaseModel):
    severity: str = Field(description="error, warning, or info")
    location: str = ""
    message: str = ""


class ReviewOutput(BaseModel):
    """Output of the AI Review stage."""

    verdict: str = Field(description="pass or needs_fixes")
    score: int = Field(ge=0, le=100, description="Quality score 0-100")
    issues: List[ReviewIssueSchema] = Field(default_factory=list)
    summary: str = ""

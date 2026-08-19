"""
Application Settings — centralized configuration for EmbedForge.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


def _parse_stage_models() -> dict:
    """Parse EMBEDFORGE_STAGE_MODELS env var (JSON mapping stage→deployment name)."""
    raw = os.getenv("EMBEDFORGE_STAGE_MODELS", "")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


# Runtime-mutable stage model overrides (set via API, takes precedence over env)
_runtime_stage_models: Optional[dict] = None

ALL_STAGES = ["refiner", "hardware", "software_arch", "software_detailed", "codegen", "codegen_mock", "codegen_test", "codegen_prod", "review", "fix_loop", "chat", "profile_generation"]


def get_stage_models() -> dict:
    if _runtime_stage_models is not None:
        return _runtime_stage_models
    return _parse_stage_models()


def set_stage_models(models: dict) -> None:
    global _runtime_stage_models
    _runtime_stage_models = models


@dataclass
class AppSettings:
    """Application-wide settings resolved from environment and defaults."""

    base_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    plugin_name: str = field(default_factory=lambda: os.getenv("EMBEDFORGE_PLUGIN", "stm32_hal"))
    output_dir: str = field(default_factory=lambda: os.getenv("EMBEDFORGE_OUTPUT_DIR", "output"))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    max_fix_iterations: int = 5
    enable_rag: bool = field(default_factory=lambda: os.getenv("EMBEDFORGE_ENABLE_RAG", "false").lower() == "true")
    allowed_sdk_roots: list = field(default_factory=lambda: [
        p.strip() for p in os.getenv("EMBEDFORGE_SDK_ROOTS", "").split(";") if p.strip()
    ])
    stage_models: dict = field(default_factory=lambda: _parse_stage_models())

    @property
    def plugins_dir(self) -> Path:
        return self.base_dir / "plugins"

    @property
    def unity_dir(self) -> Path:
        return self.base_dir / "unity"

    @property
    def output_path(self) -> Path:
        path = self.base_dir / self.output_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

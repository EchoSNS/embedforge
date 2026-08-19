"""
Application Settings — centralized configuration for EmbedForge.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


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

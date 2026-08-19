"""
Board Registry — data-driven board configuration from YAML files + Device DB.

Replaces per-board Python classes with a universal YAML schema.
Any board can be added by dropping a 5-line YAML file into the boards/ directory.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from plugins.base import BoardConfig, BoardTemplate

logger = logging.getLogger(__name__)

_BOARDS_DIR = Path(__file__).parent.parent / "boards"


def _load_board_yaml(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except (OSError, yaml.YAMLError) as e:
        logger.warning("Failed to load board YAML %s: %s", path, e)
        return None


class BoardRegistry:
    """Discovers and serves board configurations from YAML files."""

    def __init__(self, boards_dir: Optional[Path] = None) -> None:
        self._dir = boards_dir or _BOARDS_DIR
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._scan()

    def _scan(self) -> None:
        """Scan boards directory for YAML files."""
        self._cache.clear()
        if not self._dir.exists():
            return
        for yaml_file in self._dir.rglob("*.yaml"):
            data = _load_board_yaml(yaml_file)
            if data and "name" in data:
                self._cache[data["name"]] = data
                logger.debug("Loaded board: %s from %s", data["name"], yaml_file)
        if self._cache:
            logger.info("Board registry: %d boards loaded from %s", len(self._cache), self._dir)

    def list_boards(self) -> List[str]:
        return sorted(self._cache.keys())

    def get_board(self, name: str) -> Optional[Dict[str, Any]]:
        return self._cache.get(name)

    def get_template(self, name: str) -> Optional[BoardTemplate]:
        data = self._cache.get(name)
        if not data:
            return None
        return DataDrivenBoard(data)

    def refresh(self) -> None:
        self._scan()


class DataDrivenBoard(BoardTemplate):
    """A BoardTemplate backed by YAML data + Device DB lookups."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self._data = data

    def get_config(self) -> BoardConfig:
        d = self._data
        peripherals = {}

        # Build peripherals from onboard resources + device DB
        onboard = d.get("onboard", {})
        if "vcp" in onboard:
            vcp = onboard["vcp"]
            peripherals[vcp.get("peripheral", "UART0")] = {
                "type": "uart",
                "note": f"VCP ({vcp.get('tx', '?')}/{vcp.get('rx', '?')})",
            }

        # Query Device DB for full peripheral list if MCU is imported
        try:
            from core.device_db import get_device_db
            db = get_device_db()
            device_id = db.find_device(d.get("mcu", ""))
            if device_id:
                for p in db.get_peripherals(device_id):
                    if p.name not in peripherals:
                        peripherals[p.name] = {"type": p.peripheral_type.lower()}
        except Exception:
            pass

        return BoardConfig(
            name=d["name"],
            mcu=d.get("mcu", ""),
            mcu_family=d.get("family", d.get("mcu", "")[:7]),
            clock_hz=d.get("clock_hz", 0),
            peripherals=peripherals,
        )

    def get_sdk_include_paths(self) -> List[str]:
        import os
        env_var = self._data.get("sdk_env", "")
        if env_var:
            sdk_path = os.getenv(env_var, "")
            if sdk_path:
                inc_patterns = self._data.get("include_paths", [])
                return [f"{sdk_path}/{p}" for p in inc_patterns]
        return []

    def get_template_files(self) -> Dict[str, str]:
        return {}

    def get_linker_script(self) -> Optional[str]:
        return None


# Singleton
_registry: Optional[BoardRegistry] = None


def get_board_registry() -> BoardRegistry:
    global _registry
    if _registry is None:
        _registry = BoardRegistry()
    return _registry

"""
Plugin API routes — list available plugins, boards, and drivers.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter

from server.main import get_registry

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def list_plugins():
    registry = get_registry()
    active = registry.active
    logger.debug("Listing plugins: active=%s", active.name if active else None)
    return {
        "active": active.name if active else None,
        "plugins": [
            {
                "name": m.name,
                "version": m.version,
                "vendor": m.vendor,
                "description": m.description,
                "supported_mcus": m.supported_mcus,
            }
            for m in registry._plugins.values()
        ],
    }


@router.get("/boards")
async def list_boards():
    registry = get_registry()
    boards = registry.list_boards()
    logger.debug("Listing boards: %d found", len(boards))
    results = []
    for name in boards:
        board = registry.get_board_template(name)
        config = board.get_config()
        results.append({
            "name": config.name,
            "mcu": config.mcu,
            "mcu_family": config.mcu_family,
            "clock_hz": config.clock_hz,
            "peripherals": list(config.peripherals.keys()),
        })
    return results


@router.get("/drivers/{peripheral}")
async def list_drivers(peripheral: str):
    registry = get_registry()
    catalog = registry.get_driver_catalog()
    drivers = catalog.list_drivers(peripheral.upper())
    logger.debug("Listing drivers for %s: %d found", peripheral, len(drivers))
    return [
        {
            "name": d.name,
            "api_layer": d.api_layer.value,
            "description": d.description,
            "when_to_use": d.when_to_use,
        }
        for d in drivers
    ]


@router.get("/peripherals")
async def list_peripherals():
    registry = get_registry()
    catalog = registry.get_driver_catalog()
    return catalog.list_peripherals()

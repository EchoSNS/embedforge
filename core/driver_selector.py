"""
Driver Selector — picks the optimal SDK driver for a user requirement.

Given a peripheral need and complexity constraints, this module resolves
the best-fit driver from the active plugin's catalog using a scoring strategy.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from plugins.base import ApiLayer, DriverCatalog, DriverInfo, PluginRegistry

logger = logging.getLogger(__name__)


@dataclass
class SelectionCriteria:
    """User-facing requirements that influence driver selection."""

    peripheral: str
    channel_count: int = 1
    needs_complementary: bool = False
    needs_dead_time: bool = False
    needs_dma: bool = False
    needs_interrupt: bool = False
    prefer_simple: bool = False
    reference_driver: Optional[str] = None


@dataclass
class SelectionResult:
    """Outcome of driver selection with rationale."""

    driver: DriverInfo
    score: float
    rationale: str
    alternatives: List[DriverInfo]


class DriverSelector:
    """
    Scores and selects drivers based on requirement fit.

    Strategy pattern: scoring weights can be tuned per-use-case.
    """

    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry

    def select(self, criteria: SelectionCriteria) -> Optional[SelectionResult]:
        catalog = self._registry.get_driver_catalog()
        candidates = catalog.list_drivers(criteria.peripheral)

        if not candidates:
            logger.warning("No drivers found for peripheral '%s'", criteria.peripheral)
            return None

        scored = [(d, self._score(d, criteria)) for d in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)

        best, best_score = scored[0]
        alternatives = [d for d, _ in scored[1:3]]

        rationale = self._build_rationale(best, criteria)
        logger.info(
            "Driver selected: %s (score=%.2f) for %s, alternatives=%s",
            best.name, best_score, criteria.peripheral,
            [d.name for d in alternatives],
        )

        return SelectionResult(
            driver=best,
            score=best_score,
            rationale=rationale,
            alternatives=alternatives,
        )

    def _score(self, driver: DriverInfo, criteria: SelectionCriteria) -> float:
        score = 0.0

        # Prefer higher abstraction for complex requirements
        if criteria.channel_count > 1 or criteria.needs_complementary or criteria.needs_dead_time:
            if driver.api_layer == ApiLayer.UNIFIED:
                score += 30
            elif driver.api_layer == ApiLayer.HIGH_LEVEL:
                score += 20
        elif criteria.prefer_simple:
            if driver.api_layer == ApiLayer.MID_LEVEL:
                score += 25
            elif driver.api_layer == ApiLayer.LOW_LEVEL:
                score += 15

        # Penalize superseded drivers
        if driver.superseded_by:
            score -= 15

        # Bonus if handles needed capabilities internally
        if criteria.needs_dead_time and "dead_time" in " ".join(driver.handles_internally):
            score += 20
        if criteria.needs_complementary and "complementary" in " ".join(driver.handles_internally):
            score += 15

        # Bonus for matching reference driver's layer
        if criteria.reference_driver and criteria.reference_driver == driver.name:
            score += 10

        return score

    def _build_rationale(self, driver: DriverInfo, criteria: SelectionCriteria) -> str:
        parts = [f"Selected '{driver.name}' ({driver.api_layer.value}) for {criteria.peripheral}."]

        if driver.when_to_use:
            parts.append(f"Recommended for: {driver.when_to_use}")

        if criteria.needs_dead_time and "dead_time" in " ".join(driver.handles_internally):
            parts.append("Handles dead-time internally — no manual configuration needed.")

        if driver.superseded_by:
            parts.append(
                f"Note: consider upgrading to {', '.join(driver.superseded_by)} for newer projects."
            )

        return " ".join(parts)

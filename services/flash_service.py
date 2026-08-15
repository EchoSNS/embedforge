"""
Flash Service — firmware flashing via pyOCD.

Provides probe discovery, firmware flashing, and target reset
for supported debug probes (ST-LINK, CMSIS-DAP, J-Link).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProbeInfo:
    """Description of a connected debug probe."""

    unique_id: str
    vendor: str
    product: str
    target: str = ""


@dataclass
class FlashResult:
    """Outcome of a firmware flash operation."""

    success: bool
    message: str = ""
    bytes_programmed: int = 0
    duration_seconds: float = 0.0


class FlashService(ABC):
    """Abstract flash service — implementations wrap specific tools."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the flash tool is installed."""

    @abstractmethod
    def list_probes(self) -> List[ProbeInfo]:
        """Discover connected debug probes."""

    @abstractmethod
    def flash(
        self,
        binary_path: str,
        target: str = "",
        probe_id: Optional[str] = None,
    ) -> FlashResult:
        """Flash a binary (.elf/.bin/.hex) to the target."""

    @abstractmethod
    def reset(self, target: str = "", probe_id: Optional[str] = None) -> bool:
        """Reset the target MCU. Returns True on success."""


class PyOCDFlashService(FlashService):
    """
    Flash service using pyOCD (pip install pyocd).

    Supports ST-LINK, CMSIS-DAP, and J-Link probes.
    """

    def __init__(self) -> None:
        self._pyocd_available: Optional[bool] = None

    def is_available(self) -> bool:
        if self._pyocd_available is None:
            try:
                import pyocd  # noqa: F401
                self._pyocd_available = True
                logger.info("pyOCD is available (version: %s)", getattr(pyocd, "__version__", "unknown"))
            except ImportError:
                self._pyocd_available = False
                logger.debug("pyOCD not installed — flash service unavailable")
        return self._pyocd_available

    def get_info(self) -> Dict[str, Any]:
        if not self.is_available():
            return {
                "available": False,
                "message": "pyOCD not installed. Run: pip install pyocd",
            }

        import pyocd
        return {
            "available": True,
            "version": getattr(pyocd, "__version__", "unknown"),
        }

    def list_probes(self) -> List[ProbeInfo]:
        if not self.is_available():
            logger.warning("Cannot list probes — pyOCD not installed")
            return []

        try:
            from pyocd.probe import aggregator
            probes = aggregator.DebugProbeAggregator.get_all_connected_probes()

            results = []
            for p in probes:
                results.append(
                    ProbeInfo(
                        unique_id=p.unique_id,
                        vendor=getattr(p, "vendor_name", ""),
                        product=getattr(p, "product_name", ""),
                    )
                )
            logger.info("Found %d debug probe(s)", len(results))
            return results
        except Exception as e:
            logger.error("Failed to enumerate probes: %s", e)
            return []

    def flash(
        self,
        binary_path: str,
        target: str = "",
        probe_id: Optional[str] = None,
    ) -> FlashResult:
        if not self.is_available():
            logger.error("Flash requested but pyOCD is not installed")
            return FlashResult(success=False, message="pyOCD not installed")

        import time
        try:
            from pyocd.core.helpers import ConnectHelper
            from pyocd.flash.file_programmer import FileProgrammer

            connect_kwargs: Dict[str, Any] = {}
            if target:
                connect_kwargs["target_override"] = target
            if probe_id:
                connect_kwargs["unique_id"] = probe_id

            logger.info(
                "Flashing %s (target=%s, probe=%s)",
                binary_path,
                target or "auto",
                probe_id or "auto",
            )
            start = time.monotonic()

            with ConnectHelper.session(**connect_kwargs) as session:
                board = session.board
                target_obj = board.target
                programmer = FileProgrammer(session)
                programmer.program(binary_path)
                duration = time.monotonic() - start

                logger.info("Flash complete in %.2fs", duration)
                return FlashResult(
                    success=True,
                    message=f"Programmed {binary_path}",
                    duration_seconds=round(duration, 2),
                )

        except ImportError as e:
            logger.error("pyOCD import error during flash: %s", e)
            return FlashResult(success=False, message=f"pyOCD import error: {e}")
        except Exception as e:
            logger.error("Flash failed: %s", e)
            return FlashResult(success=False, message=str(e))

    def reset(self, target: str = "", probe_id: Optional[str] = None) -> bool:
        if not self.is_available():
            logger.error("Reset requested but pyOCD is not installed")
            return False

        try:
            from pyocd.core.helpers import ConnectHelper

            connect_kwargs: Dict[str, Any] = {}
            if target:
                connect_kwargs["target_override"] = target
            if probe_id:
                connect_kwargs["unique_id"] = probe_id

            logger.info("Resetting target (target=%s, probe=%s)", target or "auto", probe_id or "auto")

            with ConnectHelper.session(**connect_kwargs) as session:
                session.board.target.reset()

            logger.info("Target reset successful")
            return True
        except Exception as e:
            logger.error("Target reset failed: %s", e)
            return False

"""
CMSIS-Pack Importer — extracts device data from CMSIS-Pack (.pack) archives.

CMSIS Packs are ZIP files containing SVD files, PDSC metadata, startup code,
and flash algorithms. This importer extracts SVD files and parses PDSC for
device metadata. Works with packs from any ARM vendor (1474+ packs available).
"""

from __future__ import annotations

import logging
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import List, Optional

from core.device_data import DeviceInfo
from core.importers.svd_parser import SVDParser
from plugins.base import DeviceDataImporter

logger = logging.getLogger(__name__)


class CMSISPackImporter(DeviceDataImporter):
    """Imports device data from CMSIS-Pack (.pack) files or pack install directories."""

    @property
    def source_format(self) -> str:
        return "cmsis_pack"

    def can_import(self, path: str) -> bool:
        p = Path(path)
        if p.is_file() and p.suffix.lower() == ".pack":
            return True
        if p.is_dir():
            # Check for .pdsc file (unpacked CMSIS-Pack)
            return any(p.glob("*.pdsc"))
        return False

    def list_available_devices(self, path: str) -> List[str]:
        p = Path(path)
        devices = []

        if p.is_file() and p.suffix.lower() == ".pack":
            devices = self._list_from_pack_zip(p)
        elif p.is_dir():
            # Look for SVD files in unpacked directory
            for svd in p.rglob("*.svd"):
                devices.append(svd.stem)
            # Also check PDSC for device names
            for pdsc in p.glob("*.pdsc"):
                devices.extend(self._list_from_pdsc(pdsc))

        return sorted(set(devices))

    def import_device(self, path: str, device_name: str = "") -> Optional[DeviceInfo]:
        p = Path(path)

        if p.is_file() and p.suffix.lower() == ".pack":
            return self._import_from_pack(p, device_name)
        elif p.is_dir():
            return self._import_from_dir(p, device_name)
        return None

    def _import_from_pack(self, pack_path: Path, device_name: str) -> Optional[DeviceInfo]:
        """Extract SVD from .pack ZIP and parse it."""
        try:
            with zipfile.ZipFile(pack_path, "r") as zf:
                svd_files = [n for n in zf.namelist() if n.lower().endswith(".svd")]
                if not svd_files:
                    logger.error("No SVD files in pack: %s", pack_path)
                    return None

                # Find matching SVD
                target = None
                if device_name:
                    for sf in svd_files:
                        if device_name.lower() in sf.lower():
                            target = sf
                            break
                if not target:
                    target = svd_files[0]

                # Extract to temp and parse
                with tempfile.TemporaryDirectory() as tmp:
                    zf.extract(target, tmp)
                    svd_path = Path(tmp) / target
                    parser = SVDParser()
                    info = parser.import_device(str(svd_path))
                    if info:
                        info.source_file = str(pack_path)
                        info.source_format = "cmsis_pack"
                    return info

        except (zipfile.BadZipFile, OSError) as e:
            logger.error("Failed to read pack %s: %s", pack_path, e)
            return None

    def _import_from_dir(self, dir_path: Path, device_name: str) -> Optional[DeviceInfo]:
        """Import from an unpacked CMSIS-Pack directory."""
        parser = SVDParser()

        if device_name:
            # Find matching SVD
            for svd in dir_path.rglob("*.svd"):
                if device_name.lower() in svd.stem.lower():
                    return parser.import_device(str(svd))

        # Fall back to first SVD
        svds = list(dir_path.rglob("*.svd"))
        if svds:
            return parser.import_device(str(svds[0]))

        logger.error("No SVD files found in %s", dir_path)
        return None

    def _list_from_pack_zip(self, pack_path: Path) -> List[str]:
        """List device names from SVD files inside a .pack ZIP."""
        try:
            with zipfile.ZipFile(pack_path, "r") as zf:
                return [
                    Path(n).stem
                    for n in zf.namelist()
                    if n.lower().endswith(".svd")
                ]
        except (zipfile.BadZipFile, OSError):
            return []

    @staticmethod
    def _list_from_pdsc(pdsc_path: Path) -> List[str]:
        """Extract device names from a .pdsc file."""
        devices = []
        try:
            tree = ET.parse(pdsc_path)
            root = tree.getroot()
            ns = ""
            if root.tag.startswith("{"):
                ns = root.tag.split("}")[0] + "}"

            for dev in root.iter(f"{ns}device"):
                name = dev.get("Dname", "")
                if name:
                    devices.append(name)
        except (ET.ParseError, OSError):
            pass
        return devices

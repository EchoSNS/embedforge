"""
Device Database — local SQLite store for imported MCU hardware data.

Provides fast queries for pin-mux, peripheral instances, and register maps
across all imported devices. Populated by vendor-specific importers.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

from core.device_data import (
    DeviceInfo,
    PeripheralInstance,
    PinDirection,
    PinMuxEntry,
    Register,
    RegisterField,
)

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = Path(__file__).parent.parent / "device_data.db"


class DeviceDB:
    """SQLite-backed device data store."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._path = db_path or _DEFAULT_DB_PATH
        self._conn: Optional[sqlite3.Connection] = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._ensure_schema()
        return self._conn

    def _ensure_schema(self) -> None:
        conn = self._conn
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor TEXT NOT NULL,
                family TEXT NOT NULL,
                device TEXT NOT NULL,
                package TEXT NOT NULL DEFAULT '',
                core TEXT NOT NULL DEFAULT '',
                max_clock_hz INTEGER NOT NULL DEFAULT 0,
                source_file TEXT NOT NULL DEFAULT '',
                source_format TEXT NOT NULL DEFAULT '',
                UNIQUE(vendor, device, package)
            );

            CREATE TABLE IF NOT EXISTS pin_mux (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
                pin_name TEXT NOT NULL,
                port TEXT NOT NULL DEFAULT '',
                pin_number INTEGER NOT NULL DEFAULT 0,
                af_number INTEGER NOT NULL DEFAULT -1,
                signal TEXT NOT NULL,
                peripheral TEXT NOT NULL,
                peripheral_type TEXT NOT NULL,
                direction TEXT NOT NULL DEFAULT 'bidirectional',
                notes TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS peripherals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                peripheral_type TEXT NOT NULL,
                bus TEXT NOT NULL DEFAULT '',
                base_address INTEGER NOT NULL DEFAULT 0,
                irq_names TEXT NOT NULL DEFAULT '[]',
                features TEXT NOT NULL DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS registers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
                peripheral_name TEXT NOT NULL,
                name TEXT NOT NULL,
                offset INTEGER NOT NULL,
                size INTEGER NOT NULL DEFAULT 32,
                access TEXT NOT NULL DEFAULT 'read-write',
                description TEXT NOT NULL DEFAULT '',
                reset_value INTEGER NOT NULL DEFAULT 0,
                fields TEXT NOT NULL DEFAULT '[]'
            );

            CREATE INDEX IF NOT EXISTS idx_pin_mux_device ON pin_mux(device_id);
            CREATE INDEX IF NOT EXISTS idx_pin_mux_type ON pin_mux(device_id, peripheral_type);
            CREATE INDEX IF NOT EXISTS idx_pin_mux_signal ON pin_mux(signal);
            CREATE INDEX IF NOT EXISTS idx_peripherals_device ON peripherals(device_id);
            CREATE INDEX IF NOT EXISTS idx_registers_device ON registers(device_id, peripheral_name);
        """)
        conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # ─── Write Operations ─────────────────────────────────────────────

    def import_device(self, info: DeviceInfo) -> int:
        """Import a DeviceInfo into the database. Returns the device row ID."""
        conn = self._get_conn()

        # Upsert device row
        conn.execute("""
            INSERT INTO devices (vendor, family, device, package, core, max_clock_hz, source_file, source_format)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(vendor, device, package) DO UPDATE SET
                family=excluded.family, core=excluded.core,
                max_clock_hz=excluded.max_clock_hz,
                source_file=excluded.source_file, source_format=excluded.source_format
        """, (info.vendor, info.family, info.device, info.package,
              info.core, info.max_clock_hz, info.source_file, info.source_format))

        device_id = conn.execute(
            "SELECT id FROM devices WHERE vendor=? AND device=? AND package=?",
            (info.vendor, info.device, info.package)
        ).fetchone()["id"]

        # Clear existing data for re-import
        conn.execute("DELETE FROM pin_mux WHERE device_id=?", (device_id,))
        conn.execute("DELETE FROM peripherals WHERE device_id=?", (device_id,))
        conn.execute("DELETE FROM registers WHERE device_id=?", (device_id,))

        # Insert pin mux entries
        if info.pin_mux:
            conn.executemany("""
                INSERT INTO pin_mux (device_id, pin_name, port, pin_number, af_number,
                                     signal, peripheral, peripheral_type, direction, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                (device_id, p.pin_name, p.port, p.pin_number, p.af_number,
                 p.signal, p.peripheral, p.peripheral_type, p.direction.value, p.notes)
                for p in info.pin_mux
            ])

        # Insert peripheral instances
        if info.peripherals:
            conn.executemany("""
                INSERT INTO peripherals (device_id, name, peripheral_type, bus,
                                         base_address, irq_names, features)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [
                (device_id, p.name, p.peripheral_type, p.bus, p.base_address,
                 json.dumps(list(p.irq_names)), json.dumps(list(p.features)))
                for p in info.peripherals
            ])

        # Insert registers
        for periph_name, regs in info.registers.items():
            conn.executemany("""
                INSERT INTO registers (device_id, peripheral_name, name, offset,
                                       size, access, description, reset_value, fields)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                (device_id, periph_name, r.name, r.offset, r.size, r.access,
                 r.description, r.reset_value,
                 json.dumps([{"name": f.name, "bit_offset": f.bit_offset,
                              "bit_width": f.bit_width, "access": f.access}
                             for f in r.fields]))
                for r in regs
            ])

        conn.commit()
        logger.info("Imported device %s/%s (%s): %d pins, %d peripherals",
                    info.vendor, info.device, info.package,
                    len(info.pin_mux), len(info.peripherals))
        return device_id

    # ─── Read Operations ──────────────────────────────────────────────

    def list_devices(self) -> List[Dict]:
        """List all imported devices."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT vendor, family, device, package, core, source_format FROM devices ORDER BY vendor, family, device"
        ).fetchall()
        return [dict(r) for r in rows]

    def find_device(self, device_name: str, package: str = "") -> Optional[int]:
        """Find device ID by name (and optionally package)."""
        conn = self._get_conn()
        if package:
            row = conn.execute(
                "SELECT id FROM devices WHERE device=? AND package=?",
                (device_name, package)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT id FROM devices WHERE device=? LIMIT 1",
                (device_name,)
            ).fetchone()
        return row["id"] if row else None

    def get_pin_mux(self, device_id: int, peripheral_type: str = "") -> List[PinMuxEntry]:
        """Get pin mux entries for a device, optionally filtered by type."""
        conn = self._get_conn()
        if peripheral_type:
            rows = conn.execute(
                "SELECT * FROM pin_mux WHERE device_id=? AND peripheral_type=? ORDER BY pin_name, af_number",
                (device_id, peripheral_type.upper())
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM pin_mux WHERE device_id=? ORDER BY pin_name, af_number",
                (device_id,)
            ).fetchall()

        return [PinMuxEntry(
            pin_name=r["pin_name"], port=r["port"], pin_number=r["pin_number"],
            af_number=r["af_number"], signal=r["signal"], peripheral=r["peripheral"],
            peripheral_type=r["peripheral_type"],
            direction=PinDirection(r["direction"]), notes=r["notes"],
        ) for r in rows]

    def get_peripherals(self, device_id: int, peripheral_type: str = "") -> List[PeripheralInstance]:
        """Get peripheral instances for a device."""
        conn = self._get_conn()
        if peripheral_type:
            rows = conn.execute(
                "SELECT * FROM peripherals WHERE device_id=? AND peripheral_type=?",
                (device_id, peripheral_type.upper())
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM peripherals WHERE device_id=?", (device_id,)
            ).fetchall()

        return [PeripheralInstance(
            name=r["name"], peripheral_type=r["peripheral_type"], bus=r["bus"],
            base_address=r["base_address"],
            irq_names=tuple(json.loads(r["irq_names"])),
            features=tuple(json.loads(r["features"])),
        ) for r in rows]

    def get_pins_for_signal(self, device_id: int, signal: str) -> List[PinMuxEntry]:
        """Find which pins can carry a specific signal."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM pin_mux WHERE device_id=? AND signal LIKE ?",
            (device_id, f"%{signal}%")
        ).fetchall()
        return [PinMuxEntry(
            pin_name=r["pin_name"], port=r["port"], pin_number=r["pin_number"],
            af_number=r["af_number"], signal=r["signal"], peripheral=r["peripheral"],
            peripheral_type=r["peripheral_type"],
            direction=PinDirection(r["direction"]), notes=r["notes"],
        ) for r in rows]

    def has_device_data(self) -> bool:
        """Return True if any devices are imported."""
        conn = self._get_conn()
        row = conn.execute("SELECT COUNT(*) as cnt FROM devices").fetchone()
        return row["cnt"] > 0

    def get_device_count(self) -> int:
        conn = self._get_conn()
        row = conn.execute("SELECT COUNT(*) as cnt FROM devices").fetchone()
        return row["cnt"]

    def get_pin_count(self, device_id: int) -> int:
        conn = self._get_conn()
        row = conn.execute("SELECT COUNT(*) as cnt FROM pin_mux WHERE device_id=?", (device_id,)).fetchone()
        return row["cnt"]


# Singleton for convenience
_db_instance: Optional[DeviceDB] = None


def get_device_db() -> DeviceDB:
    global _db_instance
    if _db_instance is None:
        _db_instance = DeviceDB()
    return _db_instance

"""SQLite storage layer for the Smart Irrigation IoT System.

Creates the database and its tables automatically on first use, runs in
WAL mode, and opens one connection per thread so it is safe to call from
the MQTT network thread and the GUI thread at the same time.
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any, Iterable

SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    device_id TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    level TEXT NOT NULL,
    source TEXT NOT NULL,
    message TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS actuator_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    actuator TEXT NOT NULL,
    state TEXT NOT NULL,
    mode TEXT NOT NULL,
    reason TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_readings_timestamp ON readings (timestamp);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events (timestamp);
CREATE INDEX IF NOT EXISTS idx_actuator_states_timestamp ON actuator_states (timestamp);
"""


class Database:
    """Thread-safe SQLite access: one connection per calling thread."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_lock = threading.Lock()
        self._initialize_schema()

    def _connect(self) -> sqlite3.Connection:
        if not hasattr(self._local, "connection"):
            connection = sqlite3.connect(self.db_path, check_same_thread=False)
            connection.execute("PRAGMA journal_mode=WAL;")
            connection.execute("PRAGMA foreign_keys=ON;")
            connection.row_factory = sqlite3.Row
            self._local.connection = connection
        return self._local.connection

    def _initialize_schema(self) -> None:
        with self._init_lock:
            connection = self._connect()
            connection.executescript(SCHEMA)
            connection.commit()

    def insert_reading(self, timestamp: str, device_id: str, metric: str, value: float, unit: str) -> None:
        connection = self._connect()
        connection.execute(
            "INSERT INTO readings (timestamp, device_id, metric, value, unit) VALUES (?, ?, ?, ?, ?)",
            (timestamp, device_id, metric, value, unit),
        )
        connection.commit()

    def insert_event(self, timestamp: str, level: str, source: str, message: str) -> None:
        connection = self._connect()
        connection.execute(
            "INSERT INTO events (timestamp, level, source, message) VALUES (?, ?, ?, ?)",
            (timestamp, level, source, message),
        )
        connection.commit()

    def insert_actuator_state(self, timestamp: str, actuator: str, state: str, mode: str, reason: str) -> None:
        connection = self._connect()
        connection.execute(
            "INSERT INTO actuator_states (timestamp, actuator, state, mode, reason) VALUES (?, ?, ?, ?, ?)",
            (timestamp, actuator, state, mode, reason),
        )
        connection.commit()

    def fetch_recent_readings(self, metric: str, limit: int = 50) -> list[sqlite3.Row]:
        connection = self._connect()
        cursor = connection.execute(
            "SELECT * FROM readings WHERE metric = ? ORDER BY id DESC LIMIT ?",
            (metric, limit),
        )
        rows = cursor.fetchall()
        return list(reversed(rows))

    def fetch_recent_events(self, limit: int = 50) -> list[sqlite3.Row]:
        connection = self._connect()
        cursor = connection.execute(
            "SELECT * FROM events ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return cursor.fetchall()

    def fetch_latest_actuator_state(self, actuator: str) -> sqlite3.Row | None:
        connection = self._connect()
        cursor = connection.execute(
            "SELECT * FROM actuator_states WHERE actuator = ? ORDER BY id DESC LIMIT 1",
            (actuator,),
        )
        return cursor.fetchone()

    def close(self) -> None:
        if hasattr(self._local, "connection"):
            self._local.connection.close()
            del self._local.connection

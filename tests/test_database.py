"""Tests for the SQLite storage layer using a temporary database file."""

from pathlib import Path

from common.database import Database


def test_database_creates_schema_on_first_use(tmp_path: Path):
    db_path = tmp_path / "test.sqlite3"
    database = Database(db_path)
    assert db_path.exists()
    database.close()


def test_insert_and_fetch_readings(tmp_path: Path):
    database = Database(tmp_path / "test.sqlite3")
    database.insert_reading("2026-01-01T12:00:00Z", "dht-01", "temperature", 25.5, "C")
    database.insert_reading("2026-01-01T12:00:02Z", "dht-01", "temperature", 26.0, "C")

    rows = database.fetch_recent_readings("temperature", limit=10)
    assert len(rows) == 2
    assert rows[0]["value"] == 25.5
    assert rows[1]["value"] == 26.0
    database.close()


def test_insert_and_fetch_events(tmp_path: Path):
    database = Database(tmp_path / "test.sqlite3")
    database.insert_event("2026-01-01T12:00:00Z", "WARNING", "data-manager", "Soil is dry")

    rows = database.fetch_recent_events(limit=10)
    assert len(rows) == 1
    assert rows[0]["level"] == "WARNING"
    assert rows[0]["message"] == "Soil is dry"
    database.close()


def test_insert_and_fetch_actuator_state(tmp_path: Path):
    database = Database(tmp_path / "test.sqlite3")
    database.insert_actuator_state("2026-01-01T12:00:00Z", "pump-relay-01", "ON", "AUTO", "Soil is dry")

    latest = database.fetch_latest_actuator_state("pump-relay-01")
    assert latest is not None
    assert latest["state"] == "ON"
    assert latest["mode"] == "AUTO"
    database.close()


def test_fetch_recent_readings_returns_empty_list_when_no_data(tmp_path: Path):
    database = Database(tmp_path / "test.sqlite3")
    assert database.fetch_recent_readings("temperature") == []
    database.close()

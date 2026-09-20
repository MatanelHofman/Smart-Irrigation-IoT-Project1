"""Tests for JSON payload parsing and validation, and pump command building."""

import pytest

from common.messages import (
    DhtReading,
    InvalidMessageError,
    SoilReading,
    build_pump_command,
    parse_json,
)


def test_parse_json_accepts_valid_object():
    data = parse_json('{"device_id": "dht-01", "temperature": 25.0}')
    assert data["device_id"] == "dht-01"


def test_parse_json_rejects_malformed_json():
    with pytest.raises(InvalidMessageError):
        parse_json("{not valid json")


def test_parse_json_rejects_non_object_payload():
    with pytest.raises(InvalidMessageError):
        parse_json("[1, 2, 3]")


def test_dht_reading_from_valid_payload():
    reading = DhtReading.from_payload(
        {"device_id": "dht-01", "temperature": 27.4, "humidity": 54.1, "timestamp": "2026-01-01T12:00:00Z"}
    )
    assert reading.temperature == 27.4
    assert reading.humidity == 54.1


def test_dht_reading_missing_field_raises():
    with pytest.raises(InvalidMessageError):
        DhtReading.from_payload({"device_id": "dht-01", "temperature": 27.4})


def test_dht_reading_wrong_type_raises():
    with pytest.raises(InvalidMessageError):
        DhtReading.from_payload(
            {"device_id": "dht-01", "temperature": "hot", "humidity": 54.1, "timestamp": "x"}
        )


def test_soil_reading_from_valid_payload():
    reading = SoilReading.from_payload({"device_id": "soil-knob-01", "moisture": 24, "timestamp": "x"})
    assert reading.moisture == 24


def test_soil_reading_missing_field_raises():
    with pytest.raises(InvalidMessageError):
        SoilReading.from_payload({"device_id": "soil-knob-01"})


def test_build_pump_command_has_required_fields():
    command = build_pump_command(state="ON", mode="AUTO", reason="Soil is dry", source="data-manager")
    assert command["state"] == "ON"
    assert command["mode"] == "AUTO"
    assert command["reason"] == "Soil is dry"
    assert command["source"] == "data-manager"
    assert "timestamp" in command

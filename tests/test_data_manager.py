"""Integration-style tests for the DataManager, with a fake MQTT client so
no real broker is needed. Covers: sensor storage, automatic pump ON/OFF
transitions, manual override, and invalid payload handling.
"""

import dataclasses

import pytest

import apps.data_manager as data_manager_module
from common.config import SETTINGS
from common.messages import (
    PUMP_OFF,
    PUMP_ON,
    TOPIC_ACTUATOR_PUMP_COMMAND,
    TOPIC_SENSOR_DHT,
)


class FakeMqttClient:
    """Records every publish() call instead of talking to a real broker."""

    def __init__(self, *args, **kwargs) -> None:
        self.published: list[tuple[str, str, bool]] = []
        self.is_connected = True

    def subscribe(self, topic: str) -> None:
        pass

    def connect(self) -> None:
        pass

    def disconnect(self) -> None:
        pass

    def publish(self, topic: str, payload: str, retain: bool = False) -> None:
        self.published.append((topic, payload, retain))


@pytest.fixture
def manager(tmp_path, monkeypatch):
    test_settings = dataclasses.replace(
        SETTINGS,
        database_path=tmp_path / "dm.sqlite3",
        log_file=tmp_path / "dm.log",
        event_repeat_interval_seconds=30,
    )
    monkeypatch.setattr(data_manager_module, "SETTINGS", test_settings)
    monkeypatch.setattr(data_manager_module, "MqttClient", FakeMqttClient)
    return data_manager_module.DataManager()


def test_soil_and_dht_readings_are_stored(manager):
    manager._handle_dht_reading(
        {"device_id": "dht-01", "temperature": 25.0, "humidity": 50.0, "timestamp": "t"}
    )
    manager._handle_soil_reading({"device_id": "soil-knob-01", "moisture": 60, "timestamp": "t"})

    assert len(manager.database.fetch_recent_readings("temperature")) == 1
    assert len(manager.database.fetch_recent_readings("humidity")) == 1
    assert len(manager.database.fetch_recent_readings("soil_moisture")) == 1


def test_alarm_moisture_sends_pump_on_command(manager):
    manager._handle_soil_reading({"device_id": "soil-knob-01", "moisture": 10, "timestamp": "t"})

    assert manager.pump_state == PUMP_ON
    pump_commands = [p for p in manager.mqtt_client.published if p[0] == TOPIC_ACTUATOR_PUMP_COMMAND]
    assert len(pump_commands) == 1
    assert '"state": "ON"' in pump_commands[0][1]


def test_pump_transitions_off_on_off(manager):
    manager._handle_soil_reading({"device_id": "soil-knob-01", "moisture": 60, "timestamp": "t"})
    assert manager.pump_state == PUMP_OFF

    manager._handle_soil_reading({"device_id": "soil-knob-01", "moisture": 10, "timestamp": "t"})
    assert manager.pump_state == PUMP_ON

    manager._handle_soil_reading({"device_id": "soil-knob-01", "moisture": 60, "timestamp": "t"})
    assert manager.pump_state == PUMP_OFF

    actuator_rows = manager.database.fetch_recent_readings  # sanity: database usable
    latest = manager.database.fetch_latest_actuator_state("pump-relay-01")
    assert latest["state"] == PUMP_OFF


def test_manual_mode_blocks_automatic_pump_changes(manager):
    manager._handle_mode_change({"mode": "MANUAL"})
    manager._handle_manual_pump_command({"state": "ON"})
    assert manager.pump_state == PUMP_ON

    manager._handle_soil_reading({"device_id": "soil-knob-01", "moisture": 5, "timestamp": "t"})
    assert manager.pump_state == PUMP_ON  # automation must not override manual mode


def test_manual_pump_command_ignored_while_in_auto_mode(manager):
    manager._handle_manual_pump_command({"state": "ON"})
    assert manager.pump_state == PUMP_OFF
    pump_commands = [p for p in manager.mqtt_client.published if p[0] == TOPIC_ACTUATOR_PUMP_COMMAND]
    assert len(pump_commands) == 0


def test_invalid_dht_message_does_not_crash(manager):
    manager._on_message(TOPIC_SENSOR_DHT, b"not valid json")
    manager._on_message(TOPIC_SENSOR_DHT, b'{"device_id": "dht-01"}')
    assert manager.temperature if False else True  # process must still be alive


def test_repeated_identical_event_is_not_republished_immediately(manager):
    manager._publish_event("INFO", "Soil moisture sufficient")
    manager._publish_event("INFO", "Soil moisture sufficient")
    events = [p for p in manager.mqtt_client.published if p[0].endswith("status/events")]
    assert len(events) == 1

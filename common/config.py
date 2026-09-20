"""Central configuration loader for the Smart Irrigation IoT System.

Environment variables (from .env / the shell) hold connection settings.
config/settings.yaml holds the rule engine thresholds and device ids.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_FILE = PROJECT_ROOT / "config" / "settings.yaml"

load_dotenv(PROJECT_ROOT / ".env")


def _load_yaml_settings() -> dict[str, Any]:
    if not SETTINGS_FILE.exists():
        return {}
    with open(SETTINGS_FILE, "r", encoding="utf-8") as settings_file:
        return yaml.safe_load(settings_file) or {}


_YAML_SETTINGS = _load_yaml_settings()


@dataclass(frozen=True)
class MqttSettings:
    host: str
    port: int
    keepalive: int
    topic_prefix: str


@dataclass(frozen=True)
class SoilThresholds:
    alarm_max: int
    warning_max: int
    hysteresis_min: int
    hysteresis_max: int
    info_min: int


@dataclass(frozen=True)
class Settings:
    mqtt: MqttSettings
    soil: SoilThresholds
    temperature_warning_min_celsius: float
    event_repeat_interval_seconds: int
    dht_device_id: str
    soil_device_id: str
    pump_device_id: str
    button_device_id: str
    dht_publish_interval_seconds: float
    pump_heartbeat_interval_seconds: float
    dht_initial_temperature_celsius: float
    dht_initial_humidity_percent: float
    soil_initial_moisture_percent: int
    database_path: Path
    log_file: Path
    log_level: str


def load_settings() -> Settings:
    """Build a Settings object from environment variables + settings.yaml."""
    soil_yaml = _YAML_SETTINGS.get("soil_moisture", {})
    temperature_yaml = _YAML_SETTINGS.get("temperature", {})
    events_yaml = _YAML_SETTINGS.get("events", {})
    devices_yaml = _YAML_SETTINGS.get("devices", {})
    emulators_yaml = _YAML_SETTINGS.get("emulators", {})

    mqtt = MqttSettings(
        host=os.getenv("MQTT_HOST", "localhost"),
        port=int(os.getenv("MQTT_PORT", "1883")),
        keepalive=int(os.getenv("MQTT_KEEPALIVE", "30")),
        topic_prefix=os.getenv("MQTT_TOPIC_PREFIX", "smart_irrigation/matanel_roy"),
    )

    soil = SoilThresholds(
        alarm_max=int(soil_yaml.get("alarm_max", 20)),
        warning_max=int(soil_yaml.get("warning_max", 35)),
        hysteresis_min=int(soil_yaml.get("hysteresis_min", 36)),
        hysteresis_max=int(soil_yaml.get("hysteresis_max", 44)),
        info_min=int(soil_yaml.get("info_min", 45)),
    )

    database_path = PROJECT_ROOT / os.getenv("DATABASE_PATH", "data/smart_irrigation.sqlite3")
    log_file = PROJECT_ROOT / os.getenv("LOG_FILE", "data/data_manager.log")

    return Settings(
        mqtt=mqtt,
        soil=soil,
        temperature_warning_min_celsius=float(temperature_yaml.get("warning_min_celsius", 32)),
        event_repeat_interval_seconds=int(events_yaml.get("repeat_interval_seconds", 30)),
        dht_device_id=devices_yaml.get("dht_device_id", "dht-01"),
        soil_device_id=devices_yaml.get("soil_device_id", "soil-knob-01"),
        pump_device_id=devices_yaml.get("pump_device_id", "pump-relay-01"),
        button_device_id=devices_yaml.get("button_device_id", "control-button-01"),
        dht_publish_interval_seconds=float(emulators_yaml.get("dht_publish_interval_seconds", 2)),
        pump_heartbeat_interval_seconds=float(
            emulators_yaml.get("pump_heartbeat_interval_seconds", 5)
        ),
        dht_initial_temperature_celsius=float(
            emulators_yaml.get("dht_initial_temperature_celsius", 24.0)
        ),
        dht_initial_humidity_percent=float(
            emulators_yaml.get("dht_initial_humidity_percent", 50.0)
        ),
        soil_initial_moisture_percent=int(
            emulators_yaml.get("soil_initial_moisture_percent", 55)
        ),
        database_path=database_path,
        log_file=log_file,
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )


SETTINGS = load_settings()

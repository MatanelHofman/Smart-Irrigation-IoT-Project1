"""MQTT topic names and JSON message helpers shared by every component.

All topics live under one fixed prefix so the project does not collide
with other students on a shared broker.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from common.config import SETTINGS

PREFIX = SETTINGS.mqtt.topic_prefix

TOPIC_SENSOR_DHT = f"{PREFIX}/sensors/dht"
TOPIC_SENSOR_SOIL = f"{PREFIX}/sensors/soil"
TOPIC_CONTROL_MODE = f"{PREFIX}/control/mode"
TOPIC_CONTROL_MANUAL_PUMP = f"{PREFIX}/control/manual_pump"
TOPIC_ACTUATOR_PUMP_COMMAND = f"{PREFIX}/actuators/pump/command"
TOPIC_ACTUATOR_PUMP_STATE = f"{PREFIX}/actuators/pump/state"
TOPIC_STATUS_EVENTS = f"{PREFIX}/status/events"

QOS = 1

MODE_AUTO = "AUTO"
MODE_MANUAL = "MANUAL"

PUMP_ON = "ON"
PUMP_OFF = "OFF"

LEVEL_INFO = "INFO"
LEVEL_WARNING = "WARNING"
LEVEL_ALARM = "ALARM"


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string ending in Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def to_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


class InvalidMessageError(ValueError):
    """Raised when an incoming MQTT payload fails validation."""


def parse_json(raw_payload: bytes | str) -> dict[str, Any]:
    """Parse and validate a raw MQTT payload as a JSON object.

    Raises InvalidMessageError for malformed JSON or a non-object payload,
    so callers can log and skip the message instead of crashing.
    """
    try:
        text = raw_payload.decode("utf-8") if isinstance(raw_payload, bytes) else raw_payload
        data = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidMessageError(f"payload is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise InvalidMessageError("payload JSON must be an object")
    return data


@dataclass
class DhtReading:
    device_id: str
    temperature: float
    humidity: float
    timestamp: str

    @staticmethod
    def from_payload(payload: dict[str, Any]) -> "DhtReading":
        try:
            return DhtReading(
                device_id=str(payload["device_id"]),
                temperature=float(payload["temperature"]),
                humidity=float(payload["humidity"]),
                timestamp=str(payload["timestamp"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidMessageError(f"invalid DHT payload: {exc}") from exc


@dataclass
class SoilReading:
    device_id: str
    moisture: float
    timestamp: str

    @staticmethod
    def from_payload(payload: dict[str, Any]) -> "SoilReading":
        try:
            return SoilReading(
                device_id=str(payload["device_id"]),
                moisture=float(payload["moisture"]),
                timestamp=str(payload["timestamp"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidMessageError(f"invalid soil payload: {exc}") from exc


def build_pump_command(state: str, mode: str, reason: str, source: str) -> dict[str, Any]:
    return {
        "source": source,
        "state": state,
        "mode": mode,
        "reason": reason,
        "timestamp": utc_now_iso(),
    }


def build_status_event(level: str, source: str, message: str) -> dict[str, Any]:
    return {
        "source": source,
        "level": level,
        "message": message,
        "timestamp": utc_now_iso(),
    }


def build_mode_message(mode: str, source: str) -> dict[str, Any]:
    return {
        "source": source,
        "mode": mode,
        "timestamp": utc_now_iso(),
    }

"""Data Manager application.

Connects to the MQTT broker, collects readings from the emulators,
validates every incoming message, stores readings/events/actuator states
in SQLite, runs the rule engine, publishes Info/Warning/Alarm events, and
sends ON/OFF commands to the pump relay. Runs headless (no GUI).
"""

from __future__ import annotations

import logging
import signal
import threading
import time

from common.config import SETTINGS
from common.database import Database
from common.messages import (
    LEVEL_INFO,
    MODE_AUTO,
    MODE_MANUAL,
    PUMP_OFF,
    TOPIC_CONTROL_MANUAL_PUMP,
    TOPIC_CONTROL_MODE,
    TOPIC_SENSOR_DHT,
    TOPIC_SENSOR_SOIL,
    TOPIC_ACTUATOR_PUMP_COMMAND,
    TOPIC_STATUS_EVENTS,
    DhtReading,
    InvalidMessageError,
    SoilReading,
    build_pump_command,
    build_status_event,
    parse_json,
    to_json,
    utc_now_iso,
)
from common.mqtt_client import MqttClient
from common.rule_engine import evaluate

logger = logging.getLogger("data_manager")


def configure_logging() -> None:
    SETTINGS.log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, SETTINGS.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(SETTINGS.log_file, encoding="utf-8"),
        ],
    )


class DataManager:
    def __init__(self) -> None:
        self.database = Database(SETTINGS.database_path)
        self.mqtt_client = MqttClient(client_id="data-manager", on_message=self._on_message)

        self._lock = threading.Lock()
        self.mode = MODE_AUTO
        self.latest_temperature: float | None = None
        self.latest_moisture: float | None = None
        self.pump_state = PUMP_OFF

        self._last_published_level: str | None = None
        self._last_published_message: str | None = None
        self._last_published_time = 0.0

        self._stop_event = threading.Event()

    def start(self) -> None:
        self.mqtt_client.subscribe(TOPIC_SENSOR_DHT)
        self.mqtt_client.subscribe(TOPIC_SENSOR_SOIL)
        self.mqtt_client.subscribe(TOPIC_CONTROL_MODE)
        self.mqtt_client.subscribe(TOPIC_CONTROL_MANUAL_PUMP)
        self.mqtt_client.connect()
        logger.info("Data Manager started. Waiting for sensor data on %s", SETTINGS.mqtt.topic_prefix)

    def stop(self) -> None:
        logger.info("Shutting down Data Manager...")
        self.mqtt_client.disconnect()
        self.database.close()
        logger.info("Data Manager stopped cleanly.")

    def run_forever(self) -> None:
        self.start()
        while not self._stop_event.is_set():
            time.sleep(0.2)
        self.stop()

    def request_stop(self) -> None:
        self._stop_event.set()

    # -- MQTT message handling -------------------------------------------------

    def _on_message(self, topic: str, raw_payload: bytes) -> None:
        try:
            payload = parse_json(raw_payload)
        except InvalidMessageError as exc:
            logger.warning("Ignoring invalid message on %s: %s", topic, exc)
            return

        try:
            if topic == TOPIC_SENSOR_DHT:
                self._handle_dht_reading(payload)
            elif topic == TOPIC_SENSOR_SOIL:
                self._handle_soil_reading(payload)
            elif topic == TOPIC_CONTROL_MODE:
                self._handle_mode_change(payload)
            elif topic == TOPIC_CONTROL_MANUAL_PUMP:
                self._handle_manual_pump_command(payload)
        except InvalidMessageError as exc:
            logger.warning("Ignoring invalid message on %s: %s", topic, exc)

    def _handle_dht_reading(self, payload: dict) -> None:
        reading = DhtReading.from_payload(payload)
        timestamp = utc_now_iso()
        self.database.insert_reading(timestamp, reading.device_id, "temperature", reading.temperature, "C")
        self.database.insert_reading(timestamp, reading.device_id, "humidity", reading.humidity, "%")
        with self._lock:
            self.latest_temperature = reading.temperature
        logger.info("DHT reading: temperature=%.1fC humidity=%.1f%%", reading.temperature, reading.humidity)
        self._evaluate_rules()

    def _handle_soil_reading(self, payload: dict) -> None:
        reading = SoilReading.from_payload(payload)
        timestamp = utc_now_iso()
        self.database.insert_reading(timestamp, reading.device_id, "soil_moisture", reading.moisture, "%")
        with self._lock:
            self.latest_moisture = reading.moisture
        logger.info("Soil moisture reading: %.0f%%", reading.moisture)
        self._evaluate_rules()

    def _handle_mode_change(self, payload: dict) -> None:
        mode = str(payload.get("mode", "")).upper()
        if mode not in (MODE_AUTO, MODE_MANUAL):
            raise InvalidMessageError(f"unknown mode: {mode}")
        with self._lock:
            self.mode = mode
        logger.info("Mode changed to %s", mode)
        self._publish_event(LEVEL_INFO, f"Mode switched to {mode}", force=True)
        if mode == MODE_AUTO:
            self._evaluate_rules(force_pump_check=True)

    def _handle_manual_pump_command(self, payload: dict) -> None:
        state = str(payload.get("state", "")).upper()
        if state not in ("ON", "OFF"):
            raise InvalidMessageError(f"unknown pump state: {state}")
        with self._lock:
            if self.mode != MODE_MANUAL:
                logger.warning("Ignoring manual pump command %s: system is in %s mode", state, self.mode)
                return
            self.pump_state = state
        reason = "Manual command from Control Button"
        logger.info("Manual override: Pump %s (%s)", state, reason)
        self._send_pump_command(state, MODE_MANUAL, reason)

    # -- Rule engine -------------------------------------------------------

    def _evaluate_rules(self, force_pump_check: bool = False) -> None:
        with self._lock:
            moisture = self.latest_moisture
            temperature = self.latest_temperature
            mode = self.mode
            current_pump_state = self.pump_state

        if moisture is None:
            return

        decision = evaluate(
            moisture=moisture,
            temperature=temperature,
            thresholds=SETTINGS.soil,
            temperature_warning_min=SETTINGS.temperature_warning_min_celsius,
            mode=mode,
        )

        self._publish_event(decision.level, decision.message)

        if mode == MODE_AUTO and decision.pump_state is not None:
            if decision.pump_state != current_pump_state or force_pump_check:
                with self._lock:
                    self.pump_state = decision.pump_state
                self._send_pump_command(decision.pump_state, MODE_AUTO, decision.message)

    def _send_pump_command(self, state: str, mode: str, reason: str) -> None:
        payload = build_pump_command(state=state, mode=mode, reason=reason, source="data-manager")
        self.mqtt_client.publish(TOPIC_ACTUATOR_PUMP_COMMAND, to_json(payload), retain=True)
        self.database.insert_actuator_state(payload["timestamp"], "pump-relay-01", state, mode, reason)
        logger.info("Pump command sent: %s (mode=%s, reason=%s)", state, mode, reason)

    def _publish_event(self, level: str, message: str, force: bool = False) -> None:
        now = time.monotonic()
        same_as_last = level == self._last_published_level and message == self._last_published_message
        recently_published = (now - self._last_published_time) < SETTINGS.event_repeat_interval_seconds
        if same_as_last and recently_published and not force:
            return

        payload = build_status_event(level=level, source="data-manager", message=message)
        self.mqtt_client.publish(TOPIC_STATUS_EVENTS, to_json(payload))
        self.database.insert_event(payload["timestamp"], level, "data-manager", message)
        logger.info("[%s] %s", level, message)

        self._last_published_level = level
        self._last_published_message = message
        self._last_published_time = now


def main() -> None:
    configure_logging()
    manager = DataManager()

    def handle_signal(signum, frame) -> None:
        manager.request_stop()

    signal.signal(signal.SIGINT, handle_signal)
    try:
        signal.signal(signal.SIGTERM, handle_signal)
    except (ValueError, AttributeError):
        pass

    manager.run_forever()


if __name__ == "__main__":
    main()

"""Thin wrapper around paho-mqtt shared by every component.

Uses MQTT protocol version 3.1.1 and QoS 1 as required by the project,
and reconnects automatically if the broker connection is lost.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

import paho.mqtt.client as mqtt

from common.config import SETTINGS
from common.messages import QOS

logger = logging.getLogger(__name__)

OnMessageCallback = Callable[[str, bytes], None]


class MqttClient:
    """A small convenience wrapper with automatic reconnect and QoS 1."""

    def __init__(self, client_id: str, on_message: Optional[OnMessageCallback] = None) -> None:
        self.client_id = client_id
        self._on_message_callback = on_message
        self._connected = False

        self._client = mqtt.Client(
            client_id=client_id,
            protocol=mqtt.MQTTv311,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        self._client.on_connect = self._handle_connect
        self._client.on_disconnect = self._handle_disconnect
        self._client.on_message = self._handle_message
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)

        self._subscriptions: list[str] = []

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        self._client.connect(SETTINGS.mqtt.host, SETTINGS.mqtt.port, SETTINGS.mqtt.keepalive)
        self._client.loop_start()

    def disconnect(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()

    def subscribe(self, topic: str) -> None:
        self._subscriptions.append(topic)
        if self._connected:
            self._client.subscribe(topic, qos=QOS)

    def publish(self, topic: str, payload: str, retain: bool = False) -> None:
        self._client.publish(topic, payload, qos=QOS, retain=retain)

    def _handle_connect(self, client, userdata, flags, reason_code, properties=None) -> None:
        self._connected = reason_code == 0 or getattr(reason_code, "value", 1) == 0
        if self._connected:
            logger.info("Connected to MQTT broker at %s:%s", SETTINGS.mqtt.host, SETTINGS.mqtt.port)
            for topic in self._subscriptions:
                client.subscribe(topic, qos=QOS)
        else:
            logger.warning("MQTT connect failed with reason code: %s", reason_code)

    def _handle_disconnect(self, client, userdata, flags, reason_code, properties=None) -> None:
        self._connected = False
        logger.warning("Disconnected from MQTT broker (reason code: %s). Reconnecting...", reason_code)

    def _handle_message(self, client, userdata, message) -> None:
        if self._on_message_callback is not None:
            try:
                self._on_message_callback(message.topic, message.payload)
            except Exception:
                logger.exception("Error while handling message on topic %s", message.topic)

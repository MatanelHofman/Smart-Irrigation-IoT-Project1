"""Pump relay (actuator) emulator.

Listens for pump commands published by the Data Manager, shows the
current ON/OFF state together with the Mode and Reason it received, and
publishes an acknowledgement plus a periodic heartbeat on the pump state
topic.
"""

from __future__ import annotations

import argparse
import tkinter as tk
from tkinter import ttk

from common.config import SETTINGS
from common.messages import (
    PUMP_OFF,
    TOPIC_ACTUATOR_PUMP_COMMAND,
    TOPIC_ACTUATOR_PUMP_STATE,
    InvalidMessageError,
    parse_json,
    to_json,
    utc_now_iso,
)
from common.mqtt_client import MqttClient


class PumpRelayApp:
    def __init__(self, root: tk.Tk, device_id: str) -> None:
        self.root = root
        self.device_id = device_id
        self.state = PUMP_OFF
        self.mode = "-"
        self.reason = "no command received yet"

        self.mqtt_client = MqttClient(
            client_id=f"{device_id}-emulator", on_message=self._on_mqtt_message
        )

        root.title(f"Pump Relay - {device_id}")
        root.geometry("340x300")
        root.resizable(False, False)

        ttk.Label(root, text="Pump Relay", font=("Arial", 13, "bold")).pack(pady=(10, 4))
        ttk.Label(root, text=device_id, foreground="#555").pack()

        self.state_var = tk.StringVar()
        self.state_label = ttk.Label(root, textvariable=self.state_var, font=("Arial", 22, "bold"))
        self.state_label.pack(pady=(16, 8))

        self.mode_var = tk.StringVar()
        ttk.Label(root, textvariable=self.mode_var).pack()
        self.reason_var = tk.StringVar()
        ttk.Label(root, textvariable=self.reason_var, wraplength=300, justify="center").pack(pady=(4, 8))

        self.status_var = tk.StringVar(value="MQTT: connecting...")
        ttk.Label(root, textvariable=self.status_var, foreground="#0a6").pack(pady=(10, 4))

        self._refresh_display()
        self.mqtt_client.subscribe(TOPIC_ACTUATOR_PUMP_COMMAND)
        self.mqtt_client.connect()
        self._poll_connection_status()
        self._heartbeat()

    def _poll_connection_status(self) -> None:
        text = "MQTT: connected" if self.mqtt_client.is_connected else "MQTT: connecting..."
        self.status_var.set(text)
        self.root.after(1000, self._poll_connection_status)

    def _refresh_display(self) -> None:
        self.state_var.set(f"Pump {self.state}")
        self.state_label.config(foreground="#1e8449" if self.state == "ON" else "#7f8c8d")
        self.mode_var.set(f"Mode: {self.mode}")
        self.reason_var.set(f"Reason: {self.reason}")

    def _on_mqtt_message(self, topic: str, raw_payload: bytes) -> None:
        if topic != TOPIC_ACTUATOR_PUMP_COMMAND:
            return
        try:
            payload = parse_json(raw_payload)
            self.state = str(payload["state"])
            self.mode = str(payload.get("mode", "-"))
            self.reason = str(payload.get("reason", ""))
        except (InvalidMessageError, KeyError):
            return
        self.root.after(0, self._refresh_display)
        self.root.after(0, self._publish_state, "command_ack")

    def _publish_state(self, event: str) -> None:
        payload = {
            "device_id": self.device_id,
            "state": self.state,
            "mode": self.mode,
            "reason": self.reason,
            "event": event,
            "timestamp": utc_now_iso(),
        }
        self.mqtt_client.publish(TOPIC_ACTUATOR_PUMP_STATE, to_json(payload), retain=True)

    def _heartbeat(self) -> None:
        self._publish_state("heartbeat")
        self.root.after(int(SETTINGS.pump_heartbeat_interval_seconds * 1000), self._heartbeat)

    def on_close(self) -> None:
        self.mqtt_client.disconnect()
        self.root.destroy()


def main() -> None:
    parser = argparse.ArgumentParser(description="Pump relay emulator")
    parser.add_argument("--device-id", default=SETTINGS.pump_device_id)
    args = parser.parse_args()

    root = tk.Tk()
    app = PumpRelayApp(root, args.device_id)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()

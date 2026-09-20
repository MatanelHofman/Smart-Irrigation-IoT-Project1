"""Control button emulator.

Lets the user switch between Automatic and Manual mode, and - only while
in Manual mode - send Pump ON / Pump OFF commands by hand.
"""

from __future__ import annotations

import argparse
import tkinter as tk
from tkinter import ttk

from common.config import SETTINGS
from common.messages import (
    MODE_AUTO,
    MODE_MANUAL,
    PUMP_OFF,
    PUMP_ON,
    TOPIC_CONTROL_MANUAL_PUMP,
    TOPIC_CONTROL_MODE,
    build_mode_message,
    to_json,
    utc_now_iso,
)
from common.mqtt_client import MqttClient


class ControlButtonApp:
    def __init__(self, root: tk.Tk, device_id: str) -> None:
        self.root = root
        self.device_id = device_id
        self.mode = MODE_AUTO
        self.mqtt_client = MqttClient(client_id=f"{device_id}-emulator")

        root.title(f"Control Button - {device_id}")
        root.geometry("320x280")
        root.resizable(False, False)

        ttk.Label(root, text="Control Button", font=("Arial", 13, "bold")).pack(pady=(10, 4))
        ttk.Label(root, text=device_id, foreground="#555").pack()

        self.mode_var = tk.StringVar(value=f"Mode: {self.mode}")
        ttk.Label(root, textvariable=self.mode_var, font=("Arial", 16, "bold")).pack(pady=(16, 8))

        self.mode_button = ttk.Button(root, text="Switch to MANUAL", command=self.toggle_mode)
        self.mode_button.pack(pady=4)

        pump_frame = ttk.LabelFrame(root, text="Manual pump control")
        pump_frame.pack(pady=14, padx=16, fill="x")

        self.pump_on_button = ttk.Button(
            pump_frame, text="Pump ON", command=lambda: self.send_pump_command(PUMP_ON)
        )
        self.pump_on_button.grid(row=0, column=0, padx=8, pady=8)
        self.pump_off_button = ttk.Button(
            pump_frame, text="Pump OFF", command=lambda: self.send_pump_command(PUMP_OFF)
        )
        self.pump_off_button.grid(row=0, column=1, padx=8, pady=8)

        self.last_command_var = tk.StringVar(value="Last command: none")
        ttk.Label(root, textvariable=self.last_command_var).pack(pady=(6, 4))

        self.status_var = tk.StringVar(value="MQTT: connecting...")
        ttk.Label(root, textvariable=self.status_var, foreground="#0a6").pack(pady=(6, 4))

        self._update_pump_buttons_state()
        self.mqtt_client.connect()
        self._poll_connection_status()
        self._publish_mode()

    def _poll_connection_status(self) -> None:
        text = "MQTT: connected" if self.mqtt_client.is_connected else "MQTT: connecting..."
        self.status_var.set(text)
        self.root.after(1000, self._poll_connection_status)

    def _update_pump_buttons_state(self) -> None:
        state = "normal" if self.mode == MODE_MANUAL else "disabled"
        self.pump_on_button.config(state=state)
        self.pump_off_button.config(state=state)

    def toggle_mode(self) -> None:
        self.mode = MODE_MANUAL if self.mode == MODE_AUTO else MODE_AUTO
        self.mode_var.set(f"Mode: {self.mode}")
        self.mode_button.config(
            text="Switch to AUTO" if self.mode == MODE_MANUAL else "Switch to MANUAL"
        )
        self._update_pump_buttons_state()
        self._publish_mode()

    def _publish_mode(self) -> None:
        payload = build_mode_message(self.mode, source=self.device_id)
        self.mqtt_client.publish(TOPIC_CONTROL_MODE, to_json(payload), retain=True)

    def send_pump_command(self, state: str) -> None:
        if self.mode != MODE_MANUAL:
            return
        payload = {
            "source": self.device_id,
            "state": state,
            "timestamp": utc_now_iso(),
        }
        self.mqtt_client.publish(TOPIC_CONTROL_MANUAL_PUMP, to_json(payload), retain=True)
        self.last_command_var.set(f"Last command: Pump {state}")

    def on_close(self) -> None:
        self.mqtt_client.disconnect()
        self.root.destroy()


def main() -> None:
    parser = argparse.ArgumentParser(description="Control button emulator")
    parser.add_argument("--device-id", default=SETTINGS.button_device_id)
    args = parser.parse_args()

    root = tk.Tk()
    app = ControlButtonApp(root, args.device_id)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()

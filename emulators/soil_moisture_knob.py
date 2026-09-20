"""Soil moisture knob (slider) emulator.

The user drags a 0-100% slider to simulate the soil moisture sensor.
Every change is published over MQTT immediately, and the window shows
the current value together with a Dry / Normal / Wet label.
"""

from __future__ import annotations

import argparse
import tkinter as tk
from tkinter import ttk

from common.config import SETTINGS
from common.messages import TOPIC_SENSOR_SOIL, to_json, utc_now_iso
from common.mqtt_client import MqttClient


def moisture_state_label(moisture: int, thresholds) -> tuple[str, str]:
    """Return (label, color) for a moisture percentage."""
    if moisture <= thresholds.warning_max:
        return "Dry", "#c0392b"
    if moisture <= thresholds.hysteresis_max:
        return "Normal", "#e08e0b"
    return "Wet", "#1e8449"


class SoilMoistureKnobApp:
    def __init__(self, root: tk.Tk, device_id: str, initial_value: int) -> None:
        self.root = root
        self.device_id = device_id
        self.mqtt_client = MqttClient(client_id=f"{device_id}-emulator")

        root.title(f"Soil Moisture Knob - {device_id}")
        root.geometry("320x260")
        root.resizable(False, False)

        ttk.Label(root, text="Soil Moisture Knob", font=("Arial", 13, "bold")).pack(pady=(10, 4))
        ttk.Label(root, text=device_id, foreground="#555").pack()

        self.value_var = tk.IntVar(value=initial_value)
        self.state_var = tk.StringVar()
        self.status_var = tk.StringVar(value="MQTT: connecting...")

        self.value_label = ttk.Label(root, text="", font=("Arial", 20))
        self.value_label.pack(pady=(14, 2))

        self.slider = ttk.Scale(
            root, from_=0, to=100, orient="horizontal", length=260,
        )
        self.slider.set(initial_value)
        self.slider.pack(pady=6)

        self.state_label = ttk.Label(root, textvariable=self.state_var, font=("Arial", 13, "bold"))
        self.state_label.pack(pady=6)

        ttk.Label(root, textvariable=self.status_var, foreground="#0a6").pack(pady=(6, 4))

        # Attach the live-update command only after every widget it touches exists,
        # otherwise ttk.Scale fires it synchronously during slider.set() above.
        self.slider.config(command=self._on_slider_move)

        self.mqtt_client.connect()
        self._poll_connection_status()
        self._refresh_display(initial_value)
        self._publish(initial_value)

    def _poll_connection_status(self) -> None:
        text = "MQTT: connected" if self.mqtt_client.is_connected else "MQTT: connecting..."
        self.status_var.set(text)
        self.root.after(1000, self._poll_connection_status)

    def _refresh_display(self, moisture: int) -> None:
        self.value_label.config(text=f"Moisture: {moisture}%")
        label, color = moisture_state_label(moisture, SETTINGS.soil)
        self.state_var.set(label)
        self.state_label.config(foreground=color)

    def _publish(self, moisture: int) -> None:
        payload = {
            "device_id": self.device_id,
            "moisture": moisture,
            "timestamp": utc_now_iso(),
        }
        self.mqtt_client.publish(TOPIC_SENSOR_SOIL, to_json(payload))

    def _on_slider_move(self, value_str: str) -> None:
        moisture = round(float(value_str))
        self._refresh_display(moisture)
        self._publish(moisture)

    def on_close(self) -> None:
        self.mqtt_client.disconnect()
        self.root.destroy()


def main() -> None:
    parser = argparse.ArgumentParser(description="Soil moisture knob emulator")
    parser.add_argument("--device-id", default=SETTINGS.soil_device_id)
    parser.add_argument("--initial-value", type=int, default=SETTINGS.soil_initial_moisture_percent)
    args = parser.parse_args()

    root = tk.Tk()
    app = SoilMoistureKnobApp(root, args.device_id, args.initial_value)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()

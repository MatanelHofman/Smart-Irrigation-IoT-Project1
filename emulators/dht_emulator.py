"""DHT sensor emulator.

Publishes gradually changing temperature and humidity readings over MQTT
every few seconds, and shows a small Tkinter window with the current
values, the MQTT connection status, and Start/Stop buttons.
"""

from __future__ import annotations

import argparse
import random
import tkinter as tk
from tkinter import ttk

from common.config import SETTINGS
from common.messages import TOPIC_SENSOR_DHT, to_json, utc_now_iso
from common.mqtt_client import MqttClient

MIN_TEMPERATURE = 10.0
MAX_TEMPERATURE = 42.0
MIN_HUMIDITY = 10.0
MAX_HUMIDITY = 95.0
MAX_STEP = 0.6


class DhtEmulatorApp:
    def __init__(
        self,
        root: tk.Tk,
        device_id: str,
        initial_temperature: float,
        initial_humidity: float,
    ) -> None:
        self.root = root
        self.device_id = device_id
        self.temperature = initial_temperature
        self.humidity = initial_humidity
        self.running = False
        self._after_id: str | None = None

        self.mqtt_client = MqttClient(client_id=f"{device_id}-emulator")

        root.title(f"DHT Emulator - {device_id}")
        root.geometry("320x260")
        root.resizable(False, False)

        ttk.Label(root, text="DHT Sensor Emulator", font=("Arial", 13, "bold")).pack(pady=(10, 4))
        ttk.Label(root, text=device_id, foreground="#555").pack()

        self.temperature_var = tk.StringVar()
        self.humidity_var = tk.StringVar()
        self.status_var = tk.StringVar(value="MQTT: connecting...")

        ttk.Label(root, textvariable=self.temperature_var, font=("Arial", 20)).pack(pady=(14, 2))
        ttk.Label(root, textvariable=self.humidity_var, font=("Arial", 20)).pack(pady=2)
        ttk.Label(root, textvariable=self.status_var, foreground="#0a6").pack(pady=(10, 6))

        button_frame = ttk.Frame(root)
        button_frame.pack(pady=8)
        self.start_button = ttk.Button(button_frame, text="Start", command=self.start)
        self.start_button.grid(row=0, column=0, padx=6)
        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop, state="disabled")
        self.stop_button.grid(row=0, column=1, padx=6)

        self._update_labels()
        self.mqtt_client.connect()
        self._poll_connection_status()

    def _update_labels(self) -> None:
        self.temperature_var.set(f"Temperature: {self.temperature:.1f} C")
        self.humidity_var.set(f"Humidity: {self.humidity:.1f} %")

    def _poll_connection_status(self) -> None:
        text = "MQTT: connected" if self.mqtt_client.is_connected else "MQTT: connecting..."
        self.status_var.set(text)
        self.root.after(1000, self._poll_connection_status)

    def _random_walk(self, value: float, low: float, high: float) -> float:
        step = random.uniform(-MAX_STEP, MAX_STEP)
        return max(low, min(high, value + step))

    def _tick(self) -> None:
        if not self.running:
            return
        self.temperature = round(self._random_walk(self.temperature, MIN_TEMPERATURE, MAX_TEMPERATURE), 1)
        self.humidity = round(self._random_walk(self.humidity, MIN_HUMIDITY, MAX_HUMIDITY), 1)
        self._update_labels()
        self._publish()
        self._after_id = self.root.after(
            int(SETTINGS.dht_publish_interval_seconds * 1000), self._tick
        )

    def _publish(self) -> None:
        payload = {
            "device_id": self.device_id,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "timestamp": utc_now_iso(),
        }
        self.mqtt_client.publish(TOPIC_SENSOR_DHT, to_json(payload))

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self._tick()

    def stop(self) -> None:
        self.running = False
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        if self._after_id is not None:
            self.root.after_cancel(self._after_id)
            self._after_id = None

    def on_close(self) -> None:
        self.stop()
        self.mqtt_client.disconnect()
        self.root.destroy()


def main() -> None:
    parser = argparse.ArgumentParser(description="DHT sensor emulator")
    parser.add_argument("--device-id", default=SETTINGS.dht_device_id)
    parser.add_argument("--initial-temperature", type=float, default=SETTINGS.dht_initial_temperature_celsius)
    parser.add_argument("--initial-humidity", type=float, default=SETTINGS.dht_initial_humidity_percent)
    parser.add_argument("--autostart", action="store_true")
    args = parser.parse_args()

    root = tk.Tk()
    app = DhtEmulatorApp(root, args.device_id, args.initial_temperature, args.initial_humidity)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    if args.autostart:
        root.after(300, app.start)
    root.mainloop()


if __name__ == "__main__":
    main()

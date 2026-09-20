"""Smart Irrigation Dashboard - the main GUI application.

Shows live MQTT data plus the SQLite history: connection status,
temperature, humidity, soil moisture, pump state, automatic/manual mode,
overall INFO/WARNING/ALARM state, a chart of recent measurements and an
event log.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from common.config import SETTINGS
from common.database import Database
from common.messages import (
    LEVEL_ALARM,
    LEVEL_INFO,
    LEVEL_WARNING,
    TOPIC_ACTUATOR_PUMP_STATE,
    TOPIC_CONTROL_MODE,
    TOPIC_SENSOR_DHT,
    TOPIC_SENSOR_SOIL,
    TOPIC_STATUS_EVENTS,
    InvalidMessageError,
    parse_json,
)
from common.mqtt_client import MqttClient

REFRESH_INTERVAL_MS = 2000

LEVEL_COLORS = {
    LEVEL_INFO: "#1e8449",
    LEVEL_WARNING: "#e08e0b",
    LEVEL_ALARM: "#c0392b",
}


class DashboardApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.database = Database(SETTINGS.database_path)
        self.mqtt_client = MqttClient(client_id="main-gui", on_message=self._on_mqtt_message)

        self.temperature: float | None = None
        self.humidity: float | None = None
        self.soil_moisture: float | None = None
        self.pump_state: str = "-"
        self.mode: str = "-"
        self.overall_level: str | None = None
        self.overall_message: str = "No data yet"

        root.title("Smart Irrigation Dashboard")
        root.geometry("920x680")

        self._build_layout()
        self.mqtt_client.subscribe(TOPIC_SENSOR_DHT)
        self.mqtt_client.subscribe(TOPIC_SENSOR_SOIL)
        self.mqtt_client.subscribe(TOPIC_CONTROL_MODE)
        self.mqtt_client.subscribe(TOPIC_ACTUATOR_PUMP_STATE)
        self.mqtt_client.subscribe(TOPIC_STATUS_EVENTS)
        self.mqtt_client.connect()

        self._refresh_from_database()
        self._poll_status()

    # -- layout --------------------------------------------------------

    def _build_layout(self) -> None:
        ttk.Label(self.root, text="Smart Irrigation Dashboard", font=("Arial", 18, "bold")).pack(pady=(10, 4))

        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill="x", padx=16)
        self.mqtt_status_var = tk.StringVar(value="MQTT: connecting...")
        self.db_status_var = tk.StringVar(value="Database: connecting...")
        ttk.Label(status_frame, textvariable=self.mqtt_status_var).pack(side="left", padx=(0, 20))
        ttk.Label(status_frame, textvariable=self.db_status_var).pack(side="left")
        self.refresh_button = ttk.Button(status_frame, text="Refresh", command=self._refresh_from_database)
        self.refresh_button.pack(side="right")

        metrics_frame = ttk.LabelFrame(self.root, text="Live status")
        metrics_frame.pack(fill="x", padx=16, pady=10)

        self.temperature_var = tk.StringVar(value="Temperature: -")
        self.humidity_var = tk.StringVar(value="Humidity: -")
        self.soil_var = tk.StringVar(value="Soil Moisture: -")
        self.pump_var = tk.StringVar(value="Pump: -")
        self.mode_var = tk.StringVar(value="Mode: -")
        self.overall_var = tk.StringVar(value="Overall state: No data yet")

        labels = [
            self.temperature_var,
            self.humidity_var,
            self.soil_var,
            self.pump_var,
            self.mode_var,
        ]
        for index, var in enumerate(labels):
            ttk.Label(metrics_frame, textvariable=var, font=("Arial", 12)).grid(
                row=0, column=index, padx=14, pady=10, sticky="w"
            )

        self.overall_label = tk.Label(
            metrics_frame, textvariable=self.overall_var, font=("Arial", 13, "bold"),
            fg="white", bg="#7f8c8d", padx=10, pady=4,
        )
        self.overall_label.grid(row=1, column=0, columnspan=5, padx=14, pady=(0, 10), sticky="we")

        body_frame = ttk.Frame(self.root)
        body_frame.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        chart_frame = ttk.LabelFrame(body_frame, text="Recent measurements")
        chart_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.figure = Figure(figsize=(5.2, 4), dpi=100)
        self.axis = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        events_frame = ttk.LabelFrame(body_frame, text="Event log")
        events_frame.pack(side="left", fill="both", expand=True, padx=(8, 0))
        columns = ("timestamp", "level", "message")
        self.events_tree = ttk.Treeview(events_frame, columns=columns, show="headings", height=15)
        self.events_tree.heading("timestamp", text="Timestamp")
        self.events_tree.heading("level", text="Level")
        self.events_tree.heading("message", text="Message")
        self.events_tree.column("timestamp", width=140)
        self.events_tree.column("level", width=70, anchor="center")
        self.events_tree.column("message", width=220)
        self.events_tree.pack(fill="both", expand=True)
        for level, color in LEVEL_COLORS.items():
            self.events_tree.tag_configure(level, foreground=color)

    # -- live MQTT updates -----------------------------------------------

    def _on_mqtt_message(self, topic: str, raw_payload: bytes) -> None:
        try:
            payload = parse_json(raw_payload)
        except InvalidMessageError:
            return
        self.root.after(0, self._apply_message, topic, payload)

    def _apply_message(self, topic: str, payload: dict) -> None:
        if topic == TOPIC_SENSOR_DHT:
            self.temperature = payload.get("temperature")
            self.humidity = payload.get("humidity")
        elif topic == TOPIC_SENSOR_SOIL:
            self.soil_moisture = payload.get("moisture")
        elif topic == TOPIC_CONTROL_MODE:
            self.mode = payload.get("mode", self.mode)
        elif topic == TOPIC_ACTUATOR_PUMP_STATE:
            self.pump_state = payload.get("state", self.pump_state)
        elif topic == TOPIC_STATUS_EVENTS:
            self.overall_level = payload.get("level", self.overall_level)
            self.overall_message = payload.get("message", self.overall_message)
            self._insert_event_row(payload.get("timestamp", ""), payload.get("level", ""), payload.get("message", ""))
        self._refresh_metric_labels()

    def _refresh_metric_labels(self) -> None:
        self.temperature_var.set(
            f"Temperature: {self.temperature:.1f} C" if self.temperature is not None else "Temperature: -"
        )
        self.humidity_var.set(
            f"Humidity: {self.humidity:.1f} %" if self.humidity is not None else "Humidity: -"
        )
        self.soil_var.set(
            f"Soil Moisture: {self.soil_moisture:.0f} %" if self.soil_moisture is not None else "Soil Moisture: -"
        )
        self.pump_var.set(f"Pump: {self.pump_state}")
        self.mode_var.set(f"Mode: {self.mode}")

        if self.overall_level is None:
            self.overall_var.set("Overall state: No data yet")
            self.overall_label.config(bg="#7f8c8d")
        else:
            self.overall_var.set(f"Overall state: {self.overall_level} - {self.overall_message}")
            self.overall_label.config(bg=LEVEL_COLORS.get(self.overall_level, "#7f8c8d"))

    def _insert_event_row(self, timestamp: str, level: str, message: str) -> None:
        self.events_tree.insert("", 0, values=(timestamp, level, message), tags=(level,))
        children = self.events_tree.get_children()
        if len(children) > 200:
            for item in children[200:]:
                self.events_tree.delete(item)

    # -- status polling and DB refresh -------------------------------------

    def _poll_status(self) -> None:
        text = "MQTT: connected" if self.mqtt_client.is_connected else "MQTT: connecting..."
        self.mqtt_status_var.set(text)
        self.root.after(1000, self._poll_status)

    def _refresh_from_database(self) -> None:
        try:
            temperature_rows = self.database.fetch_recent_readings("temperature", limit=30)
            humidity_rows = self.database.fetch_recent_readings("humidity", limit=30)
            soil_rows = self.database.fetch_recent_readings("soil_moisture", limit=30)
            event_rows = self.database.fetch_recent_events(limit=50)
            self.db_status_var.set("Database: connected")
        except Exception:
            self.db_status_var.set("Database: error")
            return

        self._draw_chart(temperature_rows, humidity_rows, soil_rows)

        self.events_tree.delete(*self.events_tree.get_children())
        if not event_rows:
            self.events_tree.insert("", "end", values=("-", "-", "No data available yet"))
        else:
            for row in event_rows:
                self.events_tree.insert(
                    "", "end", values=(row["timestamp"], row["level"], row["message"]), tags=(row["level"],)
                )

    def _draw_chart(self, temperature_rows, humidity_rows, soil_rows) -> None:
        self.axis.clear()
        has_data = False
        if temperature_rows:
            self.axis.plot(
                [r["id"] for r in temperature_rows], [r["value"] for r in temperature_rows],
                label="Temperature (C)", color="#c0392b",
            )
            has_data = True
        if humidity_rows:
            self.axis.plot(
                [r["id"] for r in humidity_rows], [r["value"] for r in humidity_rows],
                label="Humidity (%)", color="#2980b9",
            )
            has_data = True
        if soil_rows:
            self.axis.plot(
                [r["id"] for r in soil_rows], [r["value"] for r in soil_rows],
                label="Soil Moisture (%)", color="#1e8449",
            )
            has_data = True

        if has_data:
            self.axis.set_xlabel("Reading #")
            self.axis.set_ylabel("Value")
            self.axis.legend(loc="upper right", fontsize=8)
        else:
            self.axis.text(0.5, 0.5, "No data available yet", ha="center", va="center")
            self.axis.set_xticks([])
            self.axis.set_yticks([])
        self.canvas.draw_idle()

    def on_close(self) -> None:
        self.mqtt_client.disconnect()
        self.database.close()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    app = DashboardApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()

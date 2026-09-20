"""Launcher for the full Smart Irrigation IoT System.

Starts the Data Manager, the Main GUI and all four emulators as separate
processes. Checks that the MQTT broker is reachable first and prints a
clear message (instead of crashing) if it is not.
"""

from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from common.config import SETTINGS  # noqa: E402

COMPONENTS = [
    ("Data Manager", ["-m", "apps.data_manager"], 1.0),
    ("Main GUI (Smart Irrigation Dashboard)", ["-m", "apps.main_gui"], 0.5),
    ("DHT Emulator", ["-m", "emulators.dht_emulator"], 0.3),
    ("Soil Moisture Knob", ["-m", "emulators.soil_moisture_knob"], 0.3),
    ("Control Button", ["-m", "emulators.control_button"], 0.3),
    ("Pump Relay", ["-m", "emulators.pump_relay"], 0.3),
]


def is_broker_reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def main() -> None:
    host, port = SETTINGS.mqtt.host, SETTINGS.mqtt.port
    print(f"Checking MQTT broker at {host}:{port} ...")
    if not is_broker_reachable(host, port):
        print(
            "\nERROR: could not reach the MQTT broker.\n"
            f"Make sure Mosquitto is running (e.g. 'docker compose up -d') and listening on {host}:{port}.\n"
            "The project will not start until the broker is reachable.\n"
        )
        sys.exit(1)
    print("Broker is reachable. Starting the system...\n")

    processes: list[subprocess.Popen] = []
    try:
        for name, args, delay in COMPONENTS:
            print(f"Starting {name} ...")
            process = subprocess.Popen([sys.executable, *args], cwd=str(PROJECT_ROOT))
            processes.append(process)
            time.sleep(delay)

        print("\nAll components started. Close any window or press Ctrl+C here to stop everything.\n")
        while True:
            time.sleep(1)
            if all(process.poll() is not None for process in processes):
                break
    except KeyboardInterrupt:
        print("\nStopping all components...")
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        print("All components stopped.")


if __name__ == "__main__":
    main()

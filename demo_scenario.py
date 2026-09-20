"""Optional helper that publishes the mandatory demo scenario automatically.

This does not replace the emulators - it is a convenience script that
plays the same steps a student would perform by hand with the Soil
Moisture Knob and Control Button, useful for quick regression checks or
recording a clean demo video.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from common.config import SETTINGS  # noqa: E402
from common.messages import (  # noqa: E402
    MODE_AUTO,
    MODE_MANUAL,
    PUMP_OFF,
    PUMP_ON,
    TOPIC_CONTROL_MANUAL_PUMP,
    TOPIC_CONTROL_MODE,
    TOPIC_SENSOR_SOIL,
    build_mode_message,
    to_json,
    utc_now_iso,
)
from common.mqtt_client import MqttClient

STEP_PAUSE_SECONDS = 12


def publish_soil(client: MqttClient, moisture: int) -> None:
    payload = {
        "device_id": SETTINGS.soil_device_id,
        "moisture": moisture,
        "timestamp": utc_now_iso(),
    }
    client.publish(TOPIC_SENSOR_SOIL, to_json(payload))
    print(f"-> published soil moisture = {moisture}%")


def main() -> None:
    client = MqttClient(client_id="demo-scenario-script")
    client.connect()
    time.sleep(1.0)

    print("Step 1: soil moisture 55% (expect INFO, pump OFF)")
    publish_soil(client, 55)
    time.sleep(STEP_PAUSE_SECONDS)

    print("Step 2: soil moisture 30% (expect WARNING, pump ON)")
    publish_soil(client, 30)
    time.sleep(STEP_PAUSE_SECONDS)

    print("Step 3: soil moisture 15% (expect ALARM)")
    publish_soil(client, 15)
    time.sleep(STEP_PAUSE_SECONDS)

    print("Step 4: soil moisture 50% (expect INFO, pump OFF)")
    publish_soil(client, 50)
    time.sleep(STEP_PAUSE_SECONDS)

    print("Step 5: switch to MANUAL mode and toggle the pump by hand")
    client.publish(TOPIC_CONTROL_MODE, to_json(build_mode_message(MODE_MANUAL, "demo-scenario-script")), retain=True)
    time.sleep(2)
    client.publish(
        TOPIC_CONTROL_MANUAL_PUMP,
        to_json({"source": "demo-scenario-script", "state": PUMP_ON, "timestamp": utc_now_iso()}),
        retain=True,
    )
    time.sleep(STEP_PAUSE_SECONDS)
    client.publish(
        TOPIC_CONTROL_MANUAL_PUMP,
        to_json({"source": "demo-scenario-script", "state": PUMP_OFF, "timestamp": utc_now_iso()}),
        retain=True,
    )
    time.sleep(2)
    client.publish(TOPIC_CONTROL_MODE, to_json(build_mode_message(MODE_AUTO, "demo-scenario-script")), retain=True)

    print("Demo scenario finished.")
    client.disconnect()


if __name__ == "__main__":
    main()

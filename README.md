# Smart Irrigation IoT System

A student project for the course **Software Development for IoT Systems in a Smart City Environment** (HIT - Holon Institute of Technology, instructor Yury Yurchenko).

The system simulates an automatic garden irrigation setup. Temperature, air humidity and soil moisture are published over MQTT by small Tkinter emulators. A Data Manager collects the readings, stores them in SQLite, runs a simple rule engine, and turns a simulated water pump on or off. A dashboard GUI shows the live and historical data, and the user can switch to manual mode and operate the pump by hand.

Authors: Matanel Hofman (213378060), Roy Binyaminovich (322659376)

GitHub: https://github.com/MatanelHofman/Smart-Irrigation-IoT-Project

## Features

- Four MQTT emulators with their own small Tkinter windows: DHT sensor, soil moisture knob, control button, pump relay.
- A Data Manager that validates every incoming message, stores readings/events/actuator states in SQLite, and runs an INFO/WARNING/ALARM rule engine with a hysteresis zone.
- A Main GUI ("Smart Irrigation Dashboard") showing live MQTT data, SQLite history, a chart, and a color-coded event log.
- Automatic mode (rule-based pump control) and manual mode (pump controlled directly from the Control Button emulator).
- All data is local: a local Mosquitto broker (via Docker Compose) and a local SQLite file. No cloud services, ML, or external APIs are used.

## Architecture

```
 DHT Emulator ---\                              /--- Pump Relay Emulator
                   \                            /
 Soil Knob Emulator -\                        /
                       >--  MQTT Broker  <----+---- Control Button Emulator
 Data Manager --------/    (Mosquitto)         \
                       \                        \
 Main GUI (Dashboard) --                         --- SQLite database
```

- Emulators and the Data Manager talk to each other **only** through MQTT.
- The Data Manager is the only component that writes to SQLite.
- The Main GUI reads live data from MQTT and history from SQLite.

## Project structure

```
apps/
    data_manager.py     Headless service: collects data, runs rules, controls the pump
    main_gui.py          Smart Irrigation Dashboard (Tkinter + Matplotlib)
emulators/
    dht_emulator.py       Temperature/humidity sensor emulator
    soil_moisture_knob.py Soil moisture slider emulator
    control_button.py     Auto/Manual mode + manual pump commands
    pump_relay.py         Pump actuator emulator
common/
    config.py    Loads .env and config/settings.yaml
    mqtt_client.py  Thin paho-mqtt wrapper (MQTT 3.1.1, QoS 1, auto-reconnect)
    messages.py     Topic names, JSON parsing/validation, message builders
    database.py     Thread-safe SQLite access (WAL mode)
    rule_engine.py  Pure rule engine (unit tested, no MQTT/SQLite dependency)
config/settings.yaml   Rule engine thresholds, device ids, emulator timing
infrastructure/mosquitto.conf   Local Mosquitto broker configuration
data/                            SQLite database and logs (created at runtime, not committed)
tests/                           pytest test suite
docs/                            README material, Hebrew scripts, screenshots
deliverables/                    Presentation, project summary, submission files
docker-compose.yml   Runs the local Mosquitto broker
run_project.py        Starts the whole system
demo_scenario.py      Optional script that plays the demo scenario automatically
```

## Installation

### Linux / macOS

```bash
docker compose up -d
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run_project.py
```

### Windows (PowerShell)

```powershell
docker compose up -d
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python run_project.py
```

`run_project.py` checks that the broker is reachable first; if Mosquitto is not running it prints a clear error message instead of crashing.

### Running components separately

Each component can also be started on its own, for example while debugging:

```bash
python -m apps.data_manager
python -m apps.main_gui
python -m emulators.dht_emulator
python -m emulators.soil_moisture_knob
python -m emulators.control_button
python -m emulators.pump_relay
```

### Using a different broker

By default the system connects to `localhost:1883`. To use another broker, copy `.env.example` to `.env` and edit `MQTT_HOST` / `MQTT_PORT`.

## MQTT topics

All topics share one fixed prefix: `smart_irrigation/matanel_roy/`.

| Topic | Published by | Retained | Payload |
|---|---|---|---|
| `sensors/dht` | DHT Emulator | no | `{device_id, temperature, humidity, timestamp}` |
| `sensors/soil` | Soil Moisture Knob | no | `{device_id, moisture, timestamp}` |
| `control/mode` | Control Button | yes | `{source, mode, timestamp}` |
| `control/manual_pump` | Control Button | yes | `{source, state, timestamp}` |
| `actuators/pump/command` | Data Manager | yes | `{source, state, mode, reason, timestamp}` |
| `actuators/pump/state` | Pump Relay | yes | `{device_id, state, mode, reason, event, timestamp}` |
| `status/events` | Data Manager | no | `{source, level, message, timestamp}` |

Example DHT payload:

```json
{
  "device_id": "dht-01",
  "temperature": 27.4,
  "humidity": 54.1,
  "timestamp": "2026-01-01T12:00:00Z"
}
```

MQTT 3.1.1, QoS 1, is used for every publish and subscribe.

## Database schema

SQLite database, created automatically on first run (`data/smart_irrigation.sqlite3`, WAL mode).

**readings**: `id, timestamp, device_id, metric, value, unit`
**events**: `id, timestamp, level, source, message`
**actuator_states**: `id, timestamp, actuator, state, mode, reason`

## Threshold rules

Configured in `config/settings.yaml`:

| Soil moisture | Level | Pump (Automatic mode) |
|---|---|---|
| 0-20% | ALARM - soil very dry | ON |
| 21-35% | WARNING - soil dry | ON |
| 36-44% | (hysteresis zone) | unchanged |
| 45%+ | INFO - moisture sufficient | OFF |

- Temperature >= 32C adds an additional WARNING.
- In Manual mode the automatic rules never change the pump; only the Control Button can.
- The same event is not re-published on every sensor message - only when the level/message changes, or after `event_repeat_interval_seconds` (default 30s).

## Demo steps

A full run-through takes about 90-120 seconds:

1. Start with Soil Moisture at 55% -> INFO, Pump OFF.
2. Lower the slider to ~30% -> WARNING, Pump ON.
3. Lower it to ~15% -> ALARM.
4. Raise it back to ~50% -> INFO, Pump OFF.
5. Switch the Control Button to Manual mode and turn the pump ON/OFF by hand.

See `docs/demo_script_he.md` for the exact narrated script (in Hebrew) and `docs/screenshots/` for real screenshots captured while running this scenario.

## Tests

```bash
pytest -q
```

37 tests cover: rule engine thresholds and hysteresis, manual override, valid/invalid payload parsing, SQLite read/write, and pump command construction. All tests use a fake MQTT client / temporary database, so no broker is required to run them.

## Troubleshooting

- **"could not reach the MQTT broker"**: make sure `docker compose up -d` succeeded and port 1883 is free. Check with `docker compose ps`.
- **GUI windows do not open**: Tkinter needs a display. On a headless Linux server, run components on a machine with a desktop, or use a virtual display (e.g. Xvfb) for testing only.
- **Database is empty in the dashboard**: click "Refresh", or check that the Data Manager process is running and connected (see its console log).
- **Old data from a previous run**: delete `data/smart_irrigation.sqlite3*` to start with an empty database (it is re-created automatically).

## Real project limitations

- All sensors and actuators are software emulators (Tkinter windows), not physical hardware.
- The broker and database are local; there is no cloud component, authentication, or multi-user support.
- The rule engine is a simple fixed-threshold engine; there is no machine learning or weather forecasting.
- This project was built and tested on Linux with a local Mosquitto broker; screenshots in `docs/screenshots/` were captured from a real run of the system.

## Authors

- Matanel Hofman, 213378060
- Roy Binyaminovich, 322659376

Course: Software Development for IoT Systems in a Smart City Environment
Instructor: Yury Yurchenko
Institution: HIT - Holon Institute of Technology

# Requirements Traceability

Maps every grading requirement to the file(s) or component that implements it.

| # | Requirement | Implemented in |
|---|---|---|
| 1 | Python 3.11+ | Entire codebase; tested with Python 3.11 and 3.12 |
| 2 | MQTT with paho-mqtt | `common/mqtt_client.py` |
| 3 | Local Mosquitto via Docker Compose | `docker-compose.yml`, `infrastructure/mosquitto.conf` |
| 4 | MQTT 3.1.1, QoS 1 | `common/mqtt_client.py` (`mqtt.MQTTv311`, `QOS = 1` in `common/messages.py`) |
| 5 | SQLite local database | `common/database.py` |
| 6 | Tkinter GUIs | `apps/main_gui.py`, `emulators/*.py` |
| 7 | Matplotlib chart | `apps/main_gui.py` (`FigureCanvasTkAgg`) |
| 8 | pytest tests | `tests/*.py` |
| 9 | Config via `.env.example` + config file | `.env.example`, `config/settings.yaml`, `common/config.py` |
| 10 | English code/UI/logs/MQTT messages | All source files under `apps/`, `emulators/`, `common/` |
| 11 | No credentials in the repository | `.gitignore` excludes `.env`; `.env.example` has no secrets |
| 12 | DHT emulator: gradual values, configurable initial value, small window, Start/Stop | `emulators/dht_emulator.py` |
| 13 | Soil moisture knob: 0-100% slider, Dry/Normal/Wet state | `emulators/soil_moisture_knob.py` |
| 14 | Control button: Auto/Manual mode, manual pump ON/OFF, last command shown | `emulators/control_button.py` |
| 15 | Pump relay: listens for commands, shows Mode/Reason, ack + heartbeat | `emulators/pump_relay.py` |
| 16 | Fixed MQTT topic prefix `smart_irrigation/matanel_roy/` | `common/config.py` (`MQTT_TOPIC_PREFIX`), `common/messages.py` |
| 17 | Retained messages for state/commands | `emulators/control_button.py`, `apps/data_manager.py`, `emulators/pump_relay.py` (`retain=True`) |
| 18 | MQTT reconnect handling | `common/mqtt_client.py` (`reconnect_delay_set`, `on_disconnect`) |
| 19 | Data Manager: connect, collect, validate, store, rules, publish, command pump, log, shutdown | `apps/data_manager.py` |
| 20 | Invalid JSON handled without crashing | `common/messages.py` (`parse_json`, `InvalidMessageError`), `apps/data_manager.py` (`_on_message`) |
| 21 | Rule thresholds (ALARM/WARNING/hysteresis/INFO) | `common/rule_engine.py`, `config/settings.yaml` |
| 22 | Temperature >= 32C additional WARNING | `common/rule_engine.py` (`evaluate`) |
| 23 | Manual mode overrides automation | `apps/data_manager.py` (`_handle_manual_pump_command`, `_evaluate_rules`) |
| 24 | No duplicate event spam | `apps/data_manager.py` (`_publish_event`, `event_repeat_interval_seconds`) |
| 25 | Thresholds outside GUI code | `config/settings.yaml` |
| 26 | SQLite auto-created, WAL mode, thread-safe | `common/database.py` |
| 27 | `readings` / `events` / `actuator_states` tables | `common/database.py` (`SCHEMA`) |
| 28 | Active DB file not committed | `.gitignore` |
| 29 | Main GUI "Smart Irrigation Dashboard" | `apps/main_gui.py` |
| 30 | GUI shows MQTT/DB status, metrics, mode, overall state, chart, event log, colors, refresh | `apps/main_gui.py` |
| 31 | "No data yet" message | `apps/main_gui.py` (`_draw_chart`, event log placeholder row) |
| 32 | `docker-compose.yml` runs only the broker | `docker-compose.yml` |
| 33 | `run_project.py` starts all components, checks broker first | `run_project.py` |
| 34 | Startup documented (Linux + Windows) | `README.md` |
| 35 | Configurable broker via `.env`, default `localhost:1883` | `.env.example`, `common/config.py` |
| 36 | Demo scenario reproducible in ~90-120s | `README.md` ("Demo steps"), `docs/demo_script_he.md` |
| 37 | Optional automatic demo script | `demo_scenario.py` |
| 38 | pytest coverage: rules, hysteresis, manual override, payload parsing, DB, pump command | `tests/test_rule_engine.py`, `tests/test_messages.py`, `tests/test_database.py`, `tests/test_data_manager.py` |
| 39 | Real screenshots from an actual run | `docs/screenshots/` |
| 40 | README: description, features, architecture, structure, install, run, topics, schema, rules, demo, tests, troubleshooting, authors, link, limitations | `README.md` |
| 41 | Requirements traceability table | this file |
| 42 | Hebrew presentation, 12 slides, RTL | `deliverables/Smart_Irrigation_Project_Presentation_HE.pptx` |
| 43 | 10-12 minute presentation script (Hebrew) | `docs/presentation_script_he.md` |
| 44 | Demo video script (Hebrew) | `docs/demo_script_he.md` |
| 45 | Missing links reported | `deliverables/MISSING_LINKS.txt` |
| 46 | Project summary DOCX + PDF from the mandatory template | `deliverables/Smart_Irrigation_Project_Summary_HE.docx`, `.pdf` |

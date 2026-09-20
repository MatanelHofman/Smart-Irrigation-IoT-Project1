"""Rule engine that turns sensor readings into events and pump decisions.

Kept free of MQTT and SQLite so it can be unit tested in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass

from common.config import SoilThresholds
from common.messages import LEVEL_ALARM, LEVEL_INFO, LEVEL_WARNING, MODE_AUTO, MODE_MANUAL, PUMP_OFF, PUMP_ON


@dataclass
class RuleDecision:
    level: str
    message: str
    pump_state: str | None
    """Pump state the automation wants, or None to leave the pump untouched
    (hysteresis zone, or manual mode is active)."""


def classify_soil_moisture(moisture: float, thresholds: SoilThresholds) -> tuple[str, str, str | None]:
    """Classify a moisture reading into (level, message, desired_pump_state).

    desired_pump_state is None inside the hysteresis zone, meaning the
    pump should keep whatever state it already had.
    """
    if moisture <= thresholds.alarm_max:
        return LEVEL_ALARM, "Soil is very dry", PUMP_ON
    if moisture <= thresholds.warning_max:
        return LEVEL_WARNING, "Soil is dry", PUMP_ON
    if moisture <= thresholds.hysteresis_max:
        return LEVEL_INFO, "Soil moisture in hysteresis zone", None
    return LEVEL_INFO, "Soil moisture sufficient", PUMP_OFF


def evaluate(
    moisture: float,
    temperature: float | None,
    thresholds: SoilThresholds,
    temperature_warning_min: float,
    mode: str,
) -> RuleDecision:
    """Evaluate the current readings and produce a single rule decision.

    In MANUAL mode the pump state is never decided by automation - the
    caller must keep whatever the user last commanded.
    """
    level, message, desired_pump_state = classify_soil_moisture(moisture, thresholds)

    if temperature is not None and temperature >= temperature_warning_min:
        if level == LEVEL_INFO:
            level = LEVEL_WARNING
        message = f"{message}; temperature high ({temperature:.1f}C)"

    if mode == MODE_MANUAL:
        desired_pump_state = None

    return RuleDecision(level=level, message=message, pump_state=desired_pump_state)

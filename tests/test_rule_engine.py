"""Tests for the rule engine: thresholds, hysteresis, manual override."""

import pytest

from common.config import SoilThresholds
from common.messages import LEVEL_ALARM, LEVEL_INFO, LEVEL_WARNING, MODE_AUTO, MODE_MANUAL, PUMP_OFF, PUMP_ON
from common.rule_engine import classify_soil_moisture, evaluate

THRESHOLDS = SoilThresholds(alarm_max=20, warning_max=35, hysteresis_min=36, hysteresis_max=44, info_min=45)
TEMP_WARNING_MIN = 32.0


@pytest.mark.parametrize("moisture", [0, 10, 20])
def test_alarm_zone_turns_pump_on(moisture):
    level, message, pump_state = classify_soil_moisture(moisture, THRESHOLDS)
    assert level == LEVEL_ALARM
    assert pump_state == PUMP_ON


@pytest.mark.parametrize("moisture", [21, 30, 35])
def test_warning_zone_turns_pump_on(moisture):
    level, message, pump_state = classify_soil_moisture(moisture, THRESHOLDS)
    assert level == LEVEL_WARNING
    assert pump_state == PUMP_ON


@pytest.mark.parametrize("moisture", [45, 60, 100])
def test_info_zone_turns_pump_off(moisture):
    level, message, pump_state = classify_soil_moisture(moisture, THRESHOLDS)
    assert level == LEVEL_INFO
    assert pump_state == PUMP_OFF


@pytest.mark.parametrize("moisture", [36, 40, 44])
def test_hysteresis_zone_does_not_change_pump(moisture):
    level, message, pump_state = classify_soil_moisture(moisture, THRESHOLDS)
    assert pump_state is None


def test_high_temperature_adds_warning_on_top_of_info():
    decision = evaluate(
        moisture=60, temperature=33.0, thresholds=THRESHOLDS,
        temperature_warning_min=TEMP_WARNING_MIN, mode=MODE_AUTO,
    )
    assert decision.level == LEVEL_WARNING
    assert "temperature" in decision.message.lower()


def test_normal_temperature_keeps_info_level():
    decision = evaluate(
        moisture=60, temperature=25.0, thresholds=THRESHOLDS,
        temperature_warning_min=TEMP_WARNING_MIN, mode=MODE_AUTO,
    )
    assert decision.level == LEVEL_INFO
    assert decision.pump_state == PUMP_OFF


def test_manual_mode_never_returns_a_pump_decision():
    decision = evaluate(
        moisture=10, temperature=25.0, thresholds=THRESHOLDS,
        temperature_warning_min=TEMP_WARNING_MIN, mode=MODE_MANUAL,
    )
    assert decision.level == LEVEL_ALARM
    assert decision.pump_state is None


def test_auto_mode_alarm_moisture_returns_pump_on():
    decision = evaluate(
        moisture=5, temperature=25.0, thresholds=THRESHOLDS,
        temperature_warning_min=TEMP_WARNING_MIN, mode=MODE_AUTO,
    )
    assert decision.pump_state == PUMP_ON

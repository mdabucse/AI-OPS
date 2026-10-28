import json
from pathlib import Path

import pytest

from day2_models import Evidence, Telemetry


SCENARIO = Path(__file__).parents[1] / "scenario.json"


def load_scenario() -> dict:
    return json.loads(SCENARIO.read_text())


def test_scenario_loads_with_expected_latency_values():
    telemetry = Telemetry.from_dict(load_scenario())

    assert telemetry.baseline_p95_latency_seconds == 0.12
    assert telemetry.current_p95_latency_seconds == 1.35


def test_pool_saturation_is_one_when_pool_is_full():
    evidence = Evidence.from_telemetry(Telemetry.from_dict(load_scenario()))

    assert evidence.pool_saturation() == 1.0


def test_latency_multiplier_is_11_25():
    evidence = Evidence.from_telemetry(Telemetry.from_dict(load_scenario()))

    assert evidence.latency_multiplier() == pytest.approx(11.25)


def test_missing_current_data_is_rejected():
    data = load_scenario()
    data.pop("current")

    with pytest.raises(ValueError, match="current"):
        Telemetry.from_dict(data)


def test_zero_pool_capacity_is_rejected():
    data = load_scenario()
    data["current"]["db_pool_max"] = 0

    with pytest.raises(ValueError, match="db_pool_max"):
        Telemetry.from_dict(data)


def test_non_finite_latency_is_rejected():
    data = load_scenario()
    data["current"]["p95_latency_seconds"] = "nan"

    with pytest.raises(ValueError, match="finite"):
        Telemetry.from_dict(data)


def test_logs_must_be_a_list_of_strings():
    data = load_scenario()
    data["logs"] = "database connection pool exhausted"

    with pytest.raises(ValueError, match="logs"):
        Telemetry.from_dict(data)

import json
from pathlib import Path

from day2_helper import run
from diagnosis import FakeModelClient


SCENARIO = Path(__file__).parents[1] / "scenario.json"


def prepare_scenario(tmp_path: Path) -> Path:
    scenario = tmp_path / "scenario.json"
    scenario.write_text(SCENARIO.read_text())
    return scenario


def test_rejected_fix_is_recorded_and_state_is_unchanged(tmp_path, monkeypatch):
    scenario = prepare_scenario(tmp_path)
    audit = tmp_path / "rejected.json"
    monkeypatch.setattr("builtins.input", lambda _: "no")

    assert run(scenario, audit, FakeModelClient()) == 0
    assert json.loads(scenario.read_text())["current"]["db_pool_max"] == 20
    assert json.loads(audit.read_text())["action_taken"] == "fix rejected; no changes made"


def test_approved_fix_is_recorded_and_state_is_changed(tmp_path, monkeypatch):
    scenario = prepare_scenario(tmp_path)
    audit = tmp_path / "approved.json"
    monkeypatch.setattr("builtins.input", lambda _: "yes")

    assert run(scenario, audit, FakeModelClient()) == 0
    assert json.loads(scenario.read_text())["current"]["db_pool_max"] == 30
    assert json.loads(audit.read_text())["action_taken"] == "pool size changed to 30"

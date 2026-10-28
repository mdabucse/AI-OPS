import json
from pathlib import Path

from day2_helper import run
from diagnosis import FakeModelClient


SCENARIO = Path(__file__).parents[1] / "scenario.json"


def copy_scenario(tmp_path: Path) -> Path:
    output = tmp_path / "scenario.json"
    output.write_text(SCENARIO.read_text())
    return output


def test_rejected_run_reports_diagnosis_and_leaves_scenario_unchanged(tmp_path, monkeypatch, capsys):
    scenario = copy_scenario(tmp_path)
    audit = tmp_path / "decision_log.json"
    monkeypatch.setattr("builtins.input", lambda _: "no")

    exit_code = run(scenario, audit, FakeModelClient())

    assert exit_code == 0
    assert "database connection pool" in capsys.readouterr().out.lower()
    assert json.loads(scenario.read_text())["current"]["db_pool_max"] == 20
    assert json.loads(audit.read_text())["human_approval"] is False


def test_approved_run_applies_fix_and_records_audit(tmp_path, monkeypatch, capsys):
    scenario = copy_scenario(tmp_path)
    audit = tmp_path / "decision_log.json"
    monkeypatch.setattr("builtins.input", lambda _: "yes")

    exit_code = run(scenario, audit, FakeModelClient())

    assert exit_code == 0
    assert "Apply this fix?" in capsys.readouterr().out
    assert json.loads(scenario.read_text())["current"]["db_pool_max"] == 30
    assert json.loads(audit.read_text())["action_taken"] == "pool size changed to 30"
    assert json.loads(audit.read_text())["recommendation"] == "Increase the simulated database pool size from 20 to 30."


def test_invalid_input_returns_nonzero_exit_code(tmp_path, monkeypatch):
    scenario = copy_scenario(tmp_path)
    scenario.write_text("not json")
    monkeypatch.setattr("builtins.input", lambda _: "no")

    audit = tmp_path / "audit.json"
    assert run(scenario, audit, FakeModelClient()) != 0
    assert json.loads(audit.read_text())["action_taken"].startswith("not attempted")


class InvalidModelClient:
    def diagnose(self, evidence):
        raise ValueError("invalid model output")


def test_invalid_model_output_returns_nonzero_exit_code(tmp_path):
    scenario = copy_scenario(tmp_path)
    audit = tmp_path / "audit.json"

    assert run(scenario, audit, InvalidModelClient()) != 0
    assert json.loads(audit.read_text())["action_taken"].startswith("not attempted")


class RecordingModelClient:
    def __init__(self):
        self.called = False

    def diagnose(self, evidence):
        self.called = True
        return FakeModelClient().diagnose(evidence)


def test_invalid_telemetry_does_not_call_model(tmp_path):
    scenario = copy_scenario(tmp_path)
    data = json.loads(scenario.read_text())
    data["logs"] = "not a list"
    scenario.write_text(json.dumps(data))
    client = RecordingModelClient()

    assert run(scenario, tmp_path / "audit.json", client) != 0
    assert client.called is False

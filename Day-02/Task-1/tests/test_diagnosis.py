import json
from pathlib import Path

import pytest

from day2_models import Evidence, Telemetry
from diagnosis import Diagnosis, FakeModelClient, OllamaClient, build_prompt


SCENARIO = Path(__file__).parents[1] / "scenario.json"


def load_evidence() -> Evidence:
    data = json.loads(SCENARIO.read_text())
    return Evidence.from_telemetry(Telemetry.from_dict(data))


def test_prompt_contains_all_operational_evidence():
    prompt = build_prompt(load_evidence())

    for expected in ("0.12", "1.35", "20", "18", "waiting for database connection"):
        assert expected in prompt


def test_valid_response_becomes_diagnosis():
    diagnosis = Diagnosis.from_dict({
        "user_impact": "Login requests are slow.",
        "root_cause": "The database pool is exhausted.",
        "evidence": ["Pool saturation is 100%"],
        "recommended_fix": "Increase the pool size.",
        "risk": "The database may receive more concurrent work.",
        "confidence": 0.95,
    })

    assert diagnosis.root_cause == "The database pool is exhausted."
    assert diagnosis.confidence == 0.95


def test_missing_required_field_is_rejected():
    data = {
        "user_impact": "Login requests are slow.",
        "root_cause": "The database pool is exhausted.",
        "evidence": [],
        "recommended_fix": "Increase the pool size.",
        "risk": "The database may receive more concurrent work.",
    }

    with pytest.raises(ValueError, match="confidence"):
        Diagnosis.from_dict(data)


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_confidence_must_be_between_zero_and_one(confidence):
    data = {
        "user_impact": "Login requests are slow.",
        "root_cause": "The database pool is exhausted.",
        "evidence": ["Pool saturation is 100%"],
        "recommended_fix": "Increase the pool size.",
        "risk": "The database may receive more concurrent work.",
        "confidence": confidence,
    }

    with pytest.raises(ValueError, match="confidence"):
        Diagnosis.from_dict(data)


def test_non_dictionary_model_response_is_rejected():
    with pytest.raises(ValueError, match="object"):
        Diagnosis.from_dict(["not", "an", "object"])


def test_empty_required_text_is_rejected():
    data = {
        "user_impact": "",
        "root_cause": "The database pool is exhausted.",
        "evidence": ["Pool saturation is 100%"],
        "recommended_fix": "Increase the pool size.",
        "risk": "The database may receive more concurrent work.",
        "confidence": 0.95,
    }

    with pytest.raises(ValueError, match="user_impact"):
        Diagnosis.from_dict(data)


def test_fake_client_returns_pool_diagnosis_without_ollama():
    diagnosis = FakeModelClient().diagnose(load_evidence())

    assert "database" in diagnosis.root_cause.lower()
    assert diagnosis.confidence >= 0.9


def test_unavailable_ollama_is_reported_as_runtime_error():
    client = OllamaClient(base_url="http://127.0.0.1:1", timeout=0.1)

    with pytest.raises(RuntimeError, match="Ollama diagnosis failed"):
        client.diagnose(load_evidence())

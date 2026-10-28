import json
from pathlib import Path

from diagnosis import Diagnosis
from day2_models import Telemetry
from remediation import (
    AuditRecord,
    FixPlan,
    apply_fix,
    request_approval,
    write_audit_record,
)


def make_telemetry() -> Telemetry:
    return Telemetry.from_dict({
        "service": "login-service",
        "baseline": {"p95_latency_seconds": 0.12},
        "current": {
            "p95_latency_seconds": 1.35,
            "db_pool_max": 20,
            "db_pool_in_use": 20,
            "db_waiting_requests": 18,
        },
        "logs": ["database connection pool exhausted"],
    })


def make_diagnosis() -> Diagnosis:
    return Diagnosis.from_dict({
        "user_impact": "Login requests are slow.",
        "root_cause": "The database pool is exhausted.",
        "evidence": ["Pool saturation is 100%"],
        "recommended_fix": "Increase the pool size from 20 to 30.",
        "risk": "The database may receive more concurrent work.",
        "confidence": 0.95,
    })


def test_yes_and_y_are_approval():
    assert request_approval(lambda _: "yes") is True
    assert request_approval(lambda _: "y") is True


def test_non_yes_answers_are_rejection():
    for answer in ("no", "n", "", "maybe"):
        assert request_approval(lambda _, answer=answer: answer) is False


def test_rejected_fix_does_not_change_pool_size():
    result = apply_fix(make_telemetry(), FixPlan.from_diagnosis(make_diagnosis()), approved=False)

    assert result.applied is False
    assert result.db_pool_max_after == 20


def test_approved_fix_changes_pool_size_to_thirty():
    result = apply_fix(make_telemetry(), FixPlan.from_diagnosis(make_diagnosis()), approved=True)

    assert result.applied is True
    assert result.db_pool_max_after == 30


def test_audit_record_contains_decision_and_action(tmp_path: Path):
    record = AuditRecord(
        diagnosis="The database pool is exhausted.",
        recommendation="Increase the pool size from 20 to 30.",
        human_approval=True,
        action_taken="pool size changed to 30",
    )
    output = tmp_path / "audit.json"

    write_audit_record(output, record)
    saved = json.loads(output.read_text())

    assert saved == {
        "diagnosis": "The database pool is exhausted.",
        "recommendation": "Increase the pool size from 20 to 30.",
        "human_approval": True,
        "action_taken": "pool size changed to 30",
    }

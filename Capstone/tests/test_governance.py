from app.db import SessionLocal, init_db
from app.governance import record_governance_event
from app.main import app
from app.models import GovernanceRecord
from app.simulation import start_login_scenario
from fastapi.testclient import TestClient


def test_governance_record_preserves_model_threshold_and_retrieval_trace():
    init_db()
    with SessionLocal() as session:
        run = start_login_scenario(session, actor="admin")
        record = record_governance_event(
            session,
            run.id,
            event_type="test.decision",
            actor="admin",
            details={
                "entity_type": "test",
                "entity_id": "test-001",
                "model_name": "zscore",
                "model_version": "1.0",
                "prompt_hash": "prompt-123",
                "retrieval_hash": "retrieval-123",
                "threshold_status": "violated",
                "policy_decision": "pending_review",
            },
        )

        assert record.correlation_id == run.correlation_id
        assert record.model_name == "zscore"
        assert record.model_version == "1.0"
        assert record.retrieval_hash == "retrieval-123"
        assert record.threshold_status == "violated"
        assert record.policy_decision == "pending_review"


def test_governance_api_requires_login_and_returns_workflow_records():
    client = TestClient(app)
    assert client.get("/api/governance?run_id=missing").status_code == 401
    client.post("/login", data={"username": "admin", "password": "admin"})
    run = client.post("/api/simulations/day2/start").json()

    response = client.get(f"/api/governance?run_id={run['run_id']}")
    assert response.status_code == 200
    events = response.json()
    assert any(event["event_type"] == "rca.created" for event in events)
    assert any(event["event_type"] == "alert.created" for event in events)
    assert all(event["correlation_id"] == run["correlation_id"] for event in events)


def test_governance_records_are_persisted():
    init_db()
    with SessionLocal() as session:
        run = start_login_scenario(session, actor="admin")
        assert session.query(GovernanceRecord).filter_by(run_id=run.id).count() >= 1

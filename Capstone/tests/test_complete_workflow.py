from app.main import app
from fastapi.testclient import TestClient


def test_complete_aiops_workflow_from_detection_to_remediation():
    client = TestClient(app)
    client.post("/login", data={"username": "admin", "password": "admin"})

    run = client.post("/api/simulations/day2/start").json()
    assert run["threshold"]["status"] == "violated"
    assert run["anomaly"]["status"] == "anomalous"
    assert run["alert"]["status"] in {"simulated", "sent"}
    assert run["rca"]["retrieved_context"]

    governance = client.get(f"/api/governance?run_id={run['run_id']}").json()
    assert any(item["event_type"] == "rca.created" for item in governance)
    assert any(item["event_type"] == "alert.created" for item in governance)

    approved = client.post(f"/api/approvals/{run['approval']['approval_id']}/approve")
    assert approved.json()["remediation"]["status"] == "applied"
    assert client.post(f"/api/approvals/{run['approval']['approval_id']}/approve").status_code == 409

    metrics = client.get(f"/api/metrics?run_id={run['run_id']}").json()
    assert metrics["current_p95_seconds"] == 0.12
    assert metrics["waiting_requests"] == 0

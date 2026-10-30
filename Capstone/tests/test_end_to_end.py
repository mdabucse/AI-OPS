from app.db import SessionLocal, init_db
from app.main import app
from app.models import AuditEvent
from app.rca_agent import create_approval_request, create_rca_finding
from app.simulation import start_login_scenario
from fastapi.testclient import TestClient


def test_phase1_end_to_end_flow():
    init_db()
    client = TestClient(app)
    assert client.post("/login", data={"username": "admin", "password": "admin"}).status_code == 200

    first_run = client.post("/api/simulations/day2/start").json()
    assert client.get(f"/api/logs?run_id={first_run['run_id']}").status_code == 200

    with SessionLocal() as session:
        first = start_login_scenario(session, actor="admin")
        first_finding = create_rca_finding(session, first.id, actor="admin")
        first_approval = create_approval_request(session, first_finding.id, actor="admin")

    pending = client.get("/api/approvals?status=pending")
    assert pending.status_code == 200
    assert any(item["approval_id"] == first_approval.id for item in pending.json())
    assert client.post(f"/api/approvals/{first_approval.id}/reject").json()["status"] == "rejected"

    second_run = client.post("/api/simulations/day2/start").json()
    assert second_run["run_id"] != first_run["run_id"]
    with SessionLocal() as session:
        second = start_login_scenario(session, actor="admin")
        second_finding = create_rca_finding(session, second.id, actor="admin")
        second_approval = create_approval_request(session, second_finding.id, actor="admin")
    assert client.post(f"/api/approvals/{second_approval.id}/approve").json()["status"] == "approved"

    with SessionLocal() as session:
        events = session.query(AuditEvent).all()
        assert any(event.event_type == "approval.rejected" for event in events)
        assert any(event.event_type == "approval.approved" for event in events)

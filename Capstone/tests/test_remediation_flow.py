import re
from time import perf_counter

from app.db import SessionLocal, init_db
from app.main import app
from app.models import AuditEvent
from app.rca_agent import decide_approval
from fastapi.testclient import TestClient


def test_one_button_creates_rca_and_approval_then_approval_recovers_metrics():
    init_db()
    client = TestClient(app)
    client.post("/login", data={"username": "admin", "password": "admin"})

    started = client.post("/api/simulations/day2/start")
    assert started.status_code == 200
    payload = started.json()
    assert payload["rca"]["root_cause"]
    assert payload["rca"]["retrieved_context"][0]["document_id"] == "runbook-db-pool-saturation"
    approval_id = payload["approval"]["approval_id"]
    run_id = payload["run_id"]

    before = client.get(f"/api/metrics?run_id={run_id}").json()
    assert before["current_p95_seconds"] == 1.35
    assert before["waiting_requests"] == 18

    decision = client.post(f"/api/approvals/{approval_id}/approve")
    assert decision.status_code == 200
    assert decision.json()["remediation"]["status"] == "applied"

    after = client.get(f"/api/metrics?run_id={run_id}").json()
    assert after["current_p95_seconds"] == 0.12
    assert after["waiting_requests"] == 0
    assert after["remediation_status"] == "applied"

    with SessionLocal() as session:
        assert session.query(AuditEvent).filter_by(event_type="remediation.applied").count() >= 1


def test_rejection_does_not_change_incident_metrics():
    init_db()
    client = TestClient(app)
    client.post("/login", data={"username": "admin", "password": "admin"})
    payload = client.post("/api/simulations/day2/start").json()

    rejected = client.post(f"/api/approvals/{payload['approval']['approval_id']}/reject")
    assert rejected.status_code == 200
    assert rejected.json()["remediation"]["status"] == "not_applied"

    metrics = client.get(f"/api/metrics?run_id={payload['run_id']}").json()
    assert metrics["current_p95_seconds"] == 1.35
    assert metrics["waiting_requests"] == 18


def test_approval_expands_pool_and_reset_restores_baseline():
    init_db()
    client = TestClient(app)
    client.post("/login", data={"username": "admin", "password": "admin"})

    reset = client.post("/api/simulations/reset")
    assert reset.status_code == 200
    assert reset.json()["pool_size"] == 20

    payload = client.post("/api/simulations/day2/start").json()
    approved = client.post(f"/api/approvals/{payload['approval']['approval_id']}/approve")
    changes = approved.json()["remediation"]["changes"]
    assert changes["pool_max_before"] == 20
    assert changes["pool_max_after"] == 40

    metrics = client.get(f"/api/metrics?run_id={payload['run_id']}").json()
    assert metrics["pool_max"] == 40

    reset_again = client.post("/api/simulations/reset")
    assert reset_again.json()["previous_pool_size"] == 40
    assert reset_again.json()["pool_size"] == 20


def test_login_timing_is_high_at_baseline_and_low_after_approval():
    init_db()
    client = TestClient(app)
    client.post("/login", data={"username": "admin", "password": "admin"})
    client.post("/api/simulations/reset")
    client.post("/logout")

    started_at = perf_counter()
    client.post("/login", data={"username": "admin", "password": "admin"})
    high_elapsed = perf_counter() - started_at
    assert high_elapsed >= 1.0
    high_dashboard = client.get("/dashboard").text
    high_ms = float(re.search(r'id="login-duration">([0-9.]+)', high_dashboard).group(1))
    assert high_ms >= 1000

    payload = client.post("/api/simulations/day2/start").json()
    client.post(f"/api/approvals/{payload['approval']['approval_id']}/approve")
    client.post("/logout")
    client.post("/login", data={"username": "admin", "password": "admin"})
    low_dashboard = client.get("/dashboard").text
    low_ms = float(re.search(r'id="login-duration">([0-9.]+)', low_dashboard).group(1))
    assert low_ms < 1000


def test_dashboard_shows_login_duration_and_rca_sections():
    client = TestClient(app)
    login = client.post(
        "/login",
        data={"username": "admin", "password": "admin"},
        follow_redirects=False,
    )
    assert login.status_code == 303
    page = client.get("/dashboard")
    assert "Login duration" in page.text
    assert "Root-cause analysis" in page.text
    assert "Traces and logs" in page.text

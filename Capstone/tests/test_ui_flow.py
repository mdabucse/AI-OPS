from app.db import SessionLocal, init_db
from app.rca_agent import create_approval_request, create_rca_finding
from app.simulation import start_login_scenario
from app.main import app
from fastapi.testclient import TestClient


def test_anonymous_users_are_redirected_to_login():
    client = TestClient(app)
    login_page = client.get("/login")
    assert "login-timing" in login_page.text
    assert "Login time" in login_page.text

    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_demo_login_simulation_logs_and_pending_approval_controls():
    init_db()
    client = TestClient(app)

    login = client.post(
        "/login",
        data={"username": "admin", "password": "admin"},
        follow_redirects=False,
    )
    assert login.status_code == 303

    dashboard = client.get("/dashboard")
    assert dashboard.status_code == 200
    assert "Run RCA simulation" in dashboard.text
    assert 'data-step="traces"' in dashboard.text
    assert 'data-step="metrics"' in dashboard.text
    assert 'data-step="rca"' in dashboard.text
    assert 'data-step="approval"' in dashboard.text
    assert 'id="pool-status"' in dashboard.text
    assert 'id="raw-timeline"' in dashboard.text
    assert 'id="call-stream"' in dashboard.text
    assert 'app.js?v=4' in dashboard.text

    script = client.get("/static/app.js?v=4")
    assert "callAndShow" in script.text
    assert "/api/rag/search" in script.text
    assert "/api/alerts?run_id=" in script.text
    assert "showStep('traces')" in script.text
    assert "showStep('metrics')" in script.text
    assert "json-explanation" in script.text
    assert "/api/simulations/reset" in script.text

    started = client.post("/api/simulations/day2/start")
    assert started.status_code == 200
    run_id = started.json()["run_id"]

    logs = client.get(f"/api/logs?run_id={run_id}")
    metrics = client.get(f"/api/metrics?run_id={run_id}")
    assert logs.status_code == 200
    assert any(log["endpoint"] == "/login" for log in logs.json())
    assert metrics.json()["current_p95_seconds"] == 1.35

    dashboard = client.get("/dashboard")
    assert "Approve" not in dashboard.text
    assert "Reject" not in dashboard.text


def test_dashboard_does_not_render_previous_simulation_records():
    init_db()
    with SessionLocal() as session:
        old_run = start_login_scenario(session, actor="admin")
        old_finding = create_rca_finding(session, old_run.id, actor="admin")
        old_approval = create_approval_request(session, old_finding.id, actor="admin")

    client = TestClient(app)
    client.post("/login", data={"username": "admin", "password": "admin"})
    dashboard = client.get("/dashboard")

    assert old_approval.id not in dashboard.text
    assert old_run.id not in dashboard.text

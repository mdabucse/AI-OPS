from app.db import SessionLocal, init_db
from app.main import app
from app.models import ThresholdEvaluation
from app.rca_agent import create_rca_finding
from app.simulation import start_login_scenario
from app.thresholds import calculate_dynamic_threshold
from fastapi.testclient import TestClient


def test_dynamic_threshold_is_derived_from_baseline():
    result = calculate_dynamic_threshold(0.12)

    assert result["baseline"] == 0.12
    assert result["threshold"] == 0.18
    assert result["method"] == "baseline_multiplier"


def test_simulation_persists_dynamic_threshold_violation():
    init_db()
    with SessionLocal() as session:
        run = start_login_scenario(session, actor="admin")
        evaluation = session.query(ThresholdEvaluation).filter_by(run_id=run.id).one()

        assert evaluation.metric_name == "login_p95_latency"
        assert evaluation.threshold_value == 0.18
        assert evaluation.observed_value == 1.35
        assert evaluation.status == "violated"

        finding = create_rca_finding(session, run.id, actor="admin")
        assert any("Dynamic threshold: 0.18s" in item for item in finding.evidence)


def test_metrics_api_exposes_dynamic_threshold():
    client = TestClient(app)
    client.post("/login", data={"username": "admin", "password": "admin"})
    run = client.post("/api/simulations/day2/start").json()

    metrics = client.get(f"/api/metrics?run_id={run['run_id']}")
    assert metrics.status_code == 200
    assert metrics.json()["dynamic_threshold_seconds"] == 0.18
    assert metrics.json()["threshold_status"] == "violated"

from app.anomaly import calculate_z_score
from app.db import SessionLocal, init_db
from app.main import app
from app.models import AnomalyEvent
from app.simulation import start_login_scenario
from fastapi.testclient import TestClient


def test_z_score_is_zero_for_baseline_value():
    assert calculate_z_score(0.12, 0.12, 0.01) == 0.0


def test_day2_simulation_persists_anomalous_latency():
    init_db()
    with SessionLocal() as session:
        run = start_login_scenario(session, actor="admin")
        anomaly = session.query(AnomalyEvent).filter_by(run_id=run.id).one()

        assert anomaly.metric_name == "login_p95_latency"
        assert anomaly.observed_value == 1.35
        assert anomaly.score > 3
        assert anomaly.status == "anomalous"
        assert anomaly.model_name == "zscore"


def test_metrics_api_exposes_anomaly_result():
    client = TestClient(app)
    client.post("/login", data={"username": "admin", "password": "admin"})
    run = client.post("/api/simulations/day2/start").json()

    metrics = client.get(f"/api/metrics?run_id={run['run_id']}").json()
    assert metrics["anomaly_status"] == "anomalous"
    assert metrics["anomaly_score"] > 3

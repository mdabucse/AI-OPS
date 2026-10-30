from app.db import SessionLocal, init_db
from app.models import ApplicationLog, SimulationRun, TelemetryEvent
from app.simulation import generate_day2_events, start_login_scenario


def test_day2_simulation_creates_latency_and_pool_evidence():
    init_db()

    with SessionLocal() as session:
        run = start_login_scenario(session, actor="admin")
        session.refresh(run)

        metric_values = {
            event.metric_name: event.value for event in run.telemetry_events
        }
        login_logs = [
            log for log in run.application_logs if log.endpoint == "/login"
        ]

        assert run.id
        assert run.correlation_id
        assert metric_values["login_p95_latency_baseline"] == 0.12
        assert metric_values["login_p95_latency_incident"] == 1.35
        assert metric_values["db_pool_max"] == 20
        assert metric_values["db_active_connections"] == 20
        assert metric_values["waiting_requests"] == 18
        assert login_logs
        assert all(log.status == 200 for log in login_logs)
        assert all(log.duration_ms >= 1350 for log in login_logs)


def test_simulation_appends_a_new_run_without_deleting_previous_runs():
    init_db()

    with SessionLocal() as session:
        first = start_login_scenario(session, actor="admin")
        second = start_login_scenario(session, actor="admin")

        assert first.id != second.id
        assert first.correlation_id != second.correlation_id
        assert session.query(SimulationRun).filter_by(id=first.id).one()
        assert session.query(SimulationRun).filter_by(id=second.id).one()


def test_generate_day2_events_is_repeatable_for_existing_run():
    init_db()

    with SessionLocal() as session:
        run = SimulationRun(
            scenario_name="day2-login-slow",
            status="running",
            correlation_id="corr-repeatable-001",
        )
        session.add(run)
        session.commit()

        generate_day2_events(session, run.id)
        first_count = session.query(TelemetryEvent).filter_by(run_id=run.id).count()
        first_log_count = session.query(ApplicationLog).filter_by(run_id=run.id).count()

        generate_day2_events(session, run.id)
        assert session.query(TelemetryEvent).filter_by(run_id=run.id).count() == first_count * 2
        assert session.query(ApplicationLog).filter_by(run_id=run.id).count() == first_log_count * 2

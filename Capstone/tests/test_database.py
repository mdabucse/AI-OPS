from datetime import datetime, timezone

from app.db import SessionLocal, create_audit_event, init_db
from app.models import ApplicationLog, SimulationRun, TelemetryEvent


def test_simulation_run_owns_metrics_and_logs():
    init_db()

    with SessionLocal() as session:
        run = SimulationRun(
            scenario_name="day2-login-slow",
            status="running",
            correlation_id="corr-test-001",
            started_at=datetime.now(timezone.utc),
        )
        session.add(run)
        session.flush()
        session.add(TelemetryEvent(
            run_id=run.id,
            metric_name="login_p95_latency",
            value=1.35,
            unit="seconds",
            timestamp=datetime.now(timezone.utc),
        ))
        session.add(ApplicationLog(
            run_id=run.id,
            level="INFO",
            message="login request completed",
            endpoint="/login",
            status=200,
            duration_ms=1350.0,
            timestamp=datetime.now(timezone.utc),
        ))
        session.commit()

        saved = session.get(SimulationRun, run.id)
        assert saved is not None
        assert len(saved.telemetry_events) == 1
        assert saved.telemetry_events[0].value == 1.35
        assert saved.application_logs[0].status == 200


def test_audit_event_preserves_correlation_id():
    init_db()

    with SessionLocal() as session:
        event = create_audit_event(
            session,
            event_type="simulation.started",
            actor="admin",
            correlation_id="corr-audit-001",
            details={"scenario": "day2-login-slow"},
        )
        session.commit()

        assert event.id is not None
        assert event.correlation_id == "corr-audit-001"
        assert event.details["scenario"] == "day2-login-slow"

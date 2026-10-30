from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import create_audit_event
from app.anomaly import detect_run_anomaly
from app.alerting import send_alert
from app.config import settings
from app.models import ApplicationLog, SimulationRun, TelemetryEvent
from app.thresholds import evaluate_dynamic_threshold


DAY2_SCENARIO = "day2-login-slow"


def generate_day2_events(session: Session, run_id: str) -> SimulationRun:
    """Append the deterministic Day 2 latency incident evidence to a run."""
    run = session.execute(select(SimulationRun).where(SimulationRun.id == run_id)).scalar_one()
    timestamp = datetime.now(timezone.utc)

    metrics = (
        ("login_p95_latency_baseline", 0.12, "seconds"),
        ("login_p95_latency_incident", 1.35, "seconds"),
        ("db_pool_max", 20, "connections"),
        ("db_active_connections", 20, "connections"),
        ("waiting_requests", 18, "requests"),
    )
    session.add_all(
        [
            TelemetryEvent(
                run_id=run.id,
                metric_name=name,
                value=value,
                unit=unit,
                timestamp=timestamp,
            )
            for name, value, unit in metrics
        ]
    )

    session.add_all(
        [
            ApplicationLog(
                run_id=run.id,
                level="INFO",
                message="Login succeeded after database connection-pool wait",
                endpoint="/login",
                status=200,
                duration_ms=1350,
                timestamp=timestamp,
            ),
            ApplicationLog(
                run_id=run.id,
                level="WARN",
                message="Database connection pool saturated; request queued",
                endpoint="/login",
                status=200,
                duration_ms=1420,
                timestamp=timestamp,
            ),
        ]
    )
    run.status = "completed"
    run.ended_at = timestamp
    evaluate_dynamic_threshold(session, run.id)
    detect_run_anomaly(session, run.id)
    send_alert(session, run.id, channel=settings.alert_channel)
    create_audit_event(
        session,
        event_type="simulation.completed",
        actor="system",
        correlation_id=run.correlation_id,
        details={"scenario": run.scenario_name, "run_id": run.id},
    )
    session.commit()
    session.refresh(run)
    return run


def start_login_scenario(session: Session, actor: str) -> SimulationRun:
    run = SimulationRun(
        scenario_name=DAY2_SCENARIO,
        status="running",
        correlation_id=str(uuid4()),
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    create_audit_event(
        session,
        event_type="simulation.started",
        actor=actor,
        correlation_id=run.correlation_id,
        details={"scenario": DAY2_SCENARIO, "run_id": run.id},
    )
    session.commit()
    return generate_day2_events(session, run.id)


def simulation_summary(run: SimulationRun) -> dict:
    metric_values = {event.metric_name: event.value for event in run.telemetry_events}
    current_p95 = metric_values.get(
        "login_p95_latency_after_remediation",
        metric_values.get("login_p95_latency_incident"),
    )
    active_connections = metric_values.get(
        "db_active_connections_after_remediation",
        metric_values.get("db_active_connections"),
    )
    waiting_requests = metric_values.get(
        "waiting_requests_after_remediation",
        metric_values.get("waiting_requests"),
    )
    pool_max = metric_values.get("db_pool_max_after_remediation", metric_values.get("db_pool_max"))
    return {
        "run_id": run.id,
        "correlation_id": run.correlation_id,
        "scenario": run.scenario_name,
        "status": run.status,
        "current_p95_seconds": current_p95,
        "pool_max": pool_max,
        "active_connections": active_connections,
        "waiting_requests": waiting_requests,
        "log_count": len(run.application_logs),
    }

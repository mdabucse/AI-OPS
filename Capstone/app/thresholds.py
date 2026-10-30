from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import create_audit_event
from app.models import SimulationRun, TelemetryEvent, ThresholdEvaluation


def calculate_dynamic_threshold(baseline: float, multiplier: float = 1.5) -> dict:
    """Calculate an explainable upper threshold from the observed baseline."""
    return {
        "baseline": baseline,
        "threshold": round(baseline * multiplier, 4),
        "method": "baseline_multiplier",
    }


def evaluate_dynamic_threshold(session: Session, run_id: str) -> ThresholdEvaluation:
    run = session.execute(select(SimulationRun).where(SimulationRun.id == run_id)).scalar_one()
    session.flush()
    events = session.execute(
        select(TelemetryEvent).where(TelemetryEvent.run_id == run.id)
    ).scalars()
    values = {event.metric_name: event.value for event in events}
    baseline = values["login_p95_latency_baseline"]
    observed = values["login_p95_latency_incident"]
    threshold = calculate_dynamic_threshold(baseline)
    evaluation = ThresholdEvaluation(
        run_id=run.id,
        metric_name="login_p95_latency",
        baseline_value=threshold["baseline"],
        threshold_value=threshold["threshold"],
        observed_value=observed,
        status="violated" if observed > threshold["threshold"] else "normal",
        method=threshold["method"],
    )
    session.add(evaluation)
    session.flush()
    create_audit_event(
        session,
        event_type="threshold.evaluated",
        actor="system",
        correlation_id=run.correlation_id,
        details={
            "run_id": run.id,
            "metric_name": evaluation.metric_name,
            "threshold": evaluation.threshold_value,
            "observed": evaluation.observed_value,
            "status": evaluation.status,
        },
    )
    return evaluation

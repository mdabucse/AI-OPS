from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import create_audit_event
from app.models import AnomalyEvent, SimulationRun, TelemetryEvent


ANOMALY_MODEL_VERSION = "1.0"


@dataclass(frozen=True)
class AnomalyResult:
    metric_name: str
    baseline_value: float
    observed_value: float
    score: float
    status: str
    model_name: str = "zscore"
    model_version: str = ANOMALY_MODEL_VERSION


def calculate_z_score(observed: float, baseline: float, deviation: float) -> float:
    """Return an explainable absolute z-score using a safe deviation floor."""
    safe_deviation = max(abs(deviation), 0.01)
    return round(abs(observed - baseline) / safe_deviation, 4)


def detect_run_anomaly(session: Session, run_id: str) -> AnomalyResult:
    run = session.execute(select(SimulationRun).where(SimulationRun.id == run_id)).scalar_one()
    session.flush()
    events = session.execute(
        select(TelemetryEvent).where(TelemetryEvent.run_id == run.id)
    ).scalars()
    values = {event.metric_name: event.value for event in events}
    baseline = values["login_p95_latency_baseline"]
    observed = values["login_p95_latency_incident"]
    result = AnomalyResult(
        metric_name="login_p95_latency",
        baseline_value=baseline,
        observed_value=observed,
        score=calculate_z_score(observed, baseline, baseline * 0.1),
        status="anomalous" if observed > baseline and calculate_z_score(observed, baseline, baseline * 0.1) >= 3 else "normal",
    )
    session.add(
        AnomalyEvent(
            run_id=run.id,
            metric_name=result.metric_name,
            baseline_value=result.baseline_value,
            observed_value=result.observed_value,
            score=result.score,
            status=result.status,
            model_name=result.model_name,
            model_version=result.model_version,
        )
    )
    create_audit_event(
        session,
        event_type="anomaly.detected",
        actor="system",
        correlation_id=run.correlation_id,
        details={
            "run_id": run.id,
            "metric_name": result.metric_name,
            "score": result.score,
            "status": result.status,
            "model_name": result.model_name,
            "model_version": result.model_version,
        },
    )
    return result

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import is_authenticated
from app.db import get_session
from app.models import AlertEvent, AnomalyEvent, ApprovalRequest, AuditEvent, SimulationRun, ThresholdEvaluation
from app.pool_state import BASELINE_POOL_SIZE, get_pool_size


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def require_user(request: Request) -> str:
    user = request.session.get("username")
    if user is None:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, session: Session = Depends(get_session)):
    if not is_authenticated(request):
        return RedirectResponse("/login", status_code=303)
    # Start every dashboard visit clean. Current-run records are loaded by the
    # simulation button; historical records remain in PostgreSQL for governance.
    approvals = []
    audits = []
    pool_size = get_pool_size(session)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "approvals": approvals,
            "audits": audits,
            "username": request.session["username"],
            "login_duration_ms": request.session.get("login_duration_ms", 0),
            "pool_size": pool_size,
            "pool_state_label": "baseline/saturated" if pool_size == BASELINE_POOL_SIZE else "expanded",
        },
    )


@router.get("/api/logs")
def logs(run_id: str, request: Request, session: Session = Depends(get_session)):
    require_user(request)
    run = session.execute(select(SimulationRun).where(SimulationRun.id == run_id)).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Simulation run not found")
    return [
        {
            "level": log.level,
            "message": log.message,
            "endpoint": log.endpoint,
            "status": log.status,
            "duration_ms": log.duration_ms,
            "timestamp": log.timestamp.isoformat(),
        }
        for log in run.application_logs
    ]


@router.get("/api/metrics")
def metrics(run_id: str, request: Request, session: Session = Depends(get_session)):
    require_user(request)
    run = session.execute(select(SimulationRun).where(SimulationRun.id == run_id)).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Simulation run not found")
    values = {event.metric_name: event.value for event in run.telemetry_events}
    threshold = session.execute(
        select(ThresholdEvaluation)
        .where(ThresholdEvaluation.run_id == run.id)
        .order_by(ThresholdEvaluation.created_at.desc())
    ).scalars().first()
    anomaly = session.execute(
        select(AnomalyEvent)
        .where(AnomalyEvent.run_id == run.id)
        .order_by(AnomalyEvent.created_at.desc())
    ).scalars().first()
    alert = session.execute(
        select(AlertEvent).where(AlertEvent.run_id == run.id).order_by(AlertEvent.created_at.desc())
    ).scalars().first()
    after_p95 = values.get("login_p95_latency_after_remediation")
    after_active = values.get("db_active_connections_after_remediation")
    after_waiting = values.get("waiting_requests_after_remediation")
    after_pool_max = values.get("db_pool_max_after_remediation")
    return {
        "run_id": run.id,
        "baseline_p95_seconds": values.get("login_p95_latency_baseline"),
        "current_p95_seconds": after_p95 if after_p95 is not None else values.get("login_p95_latency_incident"),
        "pool_max": after_pool_max if after_pool_max is not None else values.get("db_pool_max"),
        "active_connections": after_active if after_active is not None else values.get("db_active_connections"),
        "waiting_requests": after_waiting if after_waiting is not None else values.get("waiting_requests"),
        "remediation_status": "applied" if after_p95 is not None else "not_applied",
        "dynamic_threshold_seconds": threshold.threshold_value if threshold else None,
        "threshold_status": threshold.status if threshold else "not_evaluated",
        "anomaly_score": anomaly.score if anomaly else None,
        "anomaly_status": anomaly.status if anomaly else "not_evaluated",
        "anomaly_model": anomaly.model_name if anomaly else None,
        "alert_status": alert.status if alert else "not_sent",
        "alert_channel": alert.channel if alert else None,
    }

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import create_audit_event, get_session
from app.auth import current_user
from app.models import AlertEvent, AnomalyEvent, RcaFinding, SimulationRun, ThresholdEvaluation
from app.pool_state import reset_pool_size, get_pool_size
from app.rca_agent import create_approval_request, create_rca_finding
from app.simulation import simulation_summary, start_login_scenario


router = APIRouter(prefix="/api/simulations", tags=["simulations"])


@router.post("/reset")
def reset_day2_state(request: Request, session: Session = Depends(get_session)) -> dict:
    actor = current_user(request)
    if actor is None:
        raise HTTPException(status_code=401, detail="Login required")
    previous_pool_size = get_pool_size(session)
    _, pool_size = reset_pool_size(session)
    correlation_id = str(uuid4())
    create_audit_event(
        session,
        event_type="pool.reset",
        actor=actor,
        correlation_id=correlation_id,
        details={
            "previous_pool_size": previous_pool_size,
            "pool_size": pool_size,
            "reason": "training reset",
        },
    )
    session.commit()
    return {
        "status": "reset",
        "pool_size": pool_size,
        "previous_pool_size": previous_pool_size,
        "login_behavior": "The next login will be slow because the 20-connection pool is saturated.",
        "correlation_id": correlation_id,
    }


@router.post("/day2/start")
def start_day2_simulation(request: Request, session: Session = Depends(get_session)) -> dict:
    actor = current_user(request)
    if actor is None:
        raise HTTPException(status_code=401, detail="Login required")
    run = start_login_scenario(session, actor=actor)
    finding = create_rca_finding(session, run.id, actor=actor)
    approval = create_approval_request(session, finding.id, actor=actor)
    summary = simulation_summary(run)
    summary["rca"] = {
        "finding_id": finding.id,
        "root_cause": finding.root_cause,
        "evidence": finding.evidence,
        "recommendation": finding.recommendation,
        "confidence": finding.confidence,
        "retrieved_context": finding.retrieved_context,
    }
    summary["approval"] = {
        "approval_id": approval.id,
        "status": approval.status,
        "requested_action": approval.requested_action,
    }
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
        select(AlertEvent)
        .where(AlertEvent.run_id == run.id)
        .order_by(AlertEvent.created_at.desc())
    ).scalars().first()
    summary["threshold"] = {
        "value": threshold.threshold_value if threshold else None,
        "status": threshold.status if threshold else "not_evaluated",
    }
    summary["anomaly"] = {
        "score": anomaly.score if anomaly else None,
        "status": anomaly.status if anomaly else "not_evaluated",
        "model": anomaly.model_name if anomaly else None,
    }
    summary["alert"] = {
        "status": alert.status if alert else "not_sent",
        "channel": alert.channel if alert else None,
    }
    return summary


@router.get("/{run_id}")
def get_simulation(run_id: str, request: Request, session: Session = Depends(get_session)) -> dict:
    if current_user(request) is None:
        raise HTTPException(status_code=401, detail="Login required")
    run = session.execute(select(SimulationRun).where(SimulationRun.id == run_id)).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Simulation run not found")
    summary = simulation_summary(run)
    finding = session.execute(
        select(RcaFinding).where(RcaFinding.run_id == run.id).order_by(RcaFinding.id.desc())
    ).scalars().first()
    if finding:
        approval = finding.approval_requests[-1] if finding.approval_requests else None
        summary["rca"] = {
            "finding_id": finding.id,
            "root_cause": finding.root_cause,
            "evidence": finding.evidence,
            "recommendation": finding.recommendation,
            "confidence": finding.confidence,
            "retrieved_context": finding.retrieved_context,
        }
        if approval:
            summary["approval"] = {
                "approval_id": approval.id,
                "status": approval.status,
                "requested_action": approval.requested_action,
                "remediation": approval.remediation_result,
            }
    return summary

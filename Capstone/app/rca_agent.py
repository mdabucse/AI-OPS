from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import create_audit_event
from app.models import ApprovalRequest, RcaFinding, SimulationRun, ThresholdEvaluation
from app.rag import retrieve_context
from app.governance import record_governance_event
from app.remediation import apply_remediation, remediation_not_applied


def create_rca_finding(session: Session, run_id: str, actor: str) -> RcaFinding:
    run = session.execute(select(SimulationRun).where(SimulationRun.id == run_id)).scalar_one()
    metric_values = {event.metric_name: event.value for event in run.telemetry_events}
    evidence = [
        "Login P95 latency increased from 0.12s baseline to 1.35s incident",
        f"Database pool active connections reached {int(metric_values['db_active_connections'])}/"
        f"{int(metric_values['db_pool_max'])}",
        f"{int(metric_values['waiting_requests'])} requests waited for a database connection",
        "Login requests returned HTTP 200 but completed with high latency",
    ]
    retrieved_context = retrieve_context(
        "database connection pool login latency waiting requests", top_k=2
    )
    threshold = session.execute(
        select(ThresholdEvaluation)
        .where(ThresholdEvaluation.run_id == run.id)
        .order_by(ThresholdEvaluation.created_at.desc())
    ).scalars().first()
    if threshold:
        evidence.append(
            f"Dynamic threshold: {threshold.threshold_value}s; observed: "
            f"{threshold.observed_value}s; status: {threshold.status}"
        )
    evidence.extend([f"RAG source: {document['title']}" for document in retrieved_context])
    context = {
        "scenario": run.scenario_name,
        "evidence": evidence,
        "retrieved_context": retrieved_context,
    }
    context_hash = hashlib.sha256(
        json.dumps(context, sort_keys=True).encode("utf-8")
    ).hexdigest()
    finding = RcaFinding(
        run_id=run.id,
        root_cause="The login latency was caused by database connection pool saturation.",
        evidence=evidence,
        recommendation="Increase pool capacity or reduce connection hold time after validating database capacity.",
        confidence=0.94,
        model_name="day2-rule-based-rca-v1",
        context_hash=context_hash,
        retrieved_context=retrieved_context,
    )
    session.add(finding)
    session.flush()
    create_audit_event(
        session,
        event_type="rca.created",
        actor=actor,
        correlation_id=run.correlation_id,
        details={"run_id": run.id, "finding_id": finding.id, "context_hash": context_hash},
    )
    record_governance_event(
        session,
        run.id,
        event_type="rca.created",
        actor=actor,
        details={
            "entity_type": "rca_finding",
            "entity_id": finding.id,
            "model_name": finding.model_name,
            "model_version": "1.0",
            "prompt_hash": context_hash,
            "retrieval_hash": context_hash,
            "threshold_status": threshold.status if threshold else None,
            "policy_decision": "pending_review",
        },
    )
    session.commit()
    session.refresh(finding)
    return finding


def create_approval_request(session: Session, finding_id: str, actor: str) -> ApprovalRequest:
    finding = session.execute(select(RcaFinding).where(RcaFinding.id == finding_id)).scalar_one()
    approval = ApprovalRequest(
        finding_id=finding.id,
        status="pending",
        requested_action=finding.recommendation,
    )
    session.add(approval)
    session.flush()
    create_audit_event(
        session,
        event_type="approval.requested",
        actor=actor,
        correlation_id=finding.run.correlation_id,
        details={"finding_id": finding.id, "approval_id": approval.id},
    )
    record_governance_event(
        session,
        finding.run.id,
        event_type="approval.requested",
        actor=actor,
        details={
            "entity_type": "approval_request",
            "entity_id": approval.id,
            "policy_decision": "pending_review",
        },
    )
    session.commit()
    session.refresh(approval)
    return approval


def decide_approval(session: Session, approval_id: str, actor: str, decision: str) -> ApprovalRequest:
    if decision not in {"approved", "rejected"}:
        raise ValueError("decision must be approved or rejected")
    approval = session.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == approval_id).with_for_update()
    ).scalar_one()
    if approval.status != "pending":
        raise ValueError("approval already decided")

    approval.status = decision
    approval.decided_by = actor
    approval.decided_at = datetime.now(timezone.utc)
    approval.remediation_result = (
        apply_remediation(session, approval, actor)
        if decision == "approved"
        else remediation_not_applied()
    )
    create_audit_event(
        session,
        event_type=f"approval.{decision}",
        actor=actor,
        correlation_id=approval.finding.run.correlation_id,
        details={"approval_id": approval.id, "finding_id": approval.finding_id},
    )
    record_governance_event(
        session,
        approval.finding.run.id,
        event_type=f"approval.{decision}",
        actor=actor,
        details={
            "entity_type": "approval_request",
            "entity_id": approval.id,
            "policy_decision": decision,
        },
    )
    session.commit()
    session.refresh(approval)
    return approval

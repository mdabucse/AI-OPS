from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import GovernanceRecord, SimulationRun


def record_governance_event(
    session: Session,
    run_id: str,
    event_type: str,
    actor: str,
    details: dict,
) -> GovernanceRecord:
    run = session.execute(select(SimulationRun).where(SimulationRun.id == run_id)).scalar_one()
    record = GovernanceRecord(
        run_id=run.id,
        event_type=event_type,
        entity_type=details.get("entity_type", "workflow"),
        entity_id=str(details.get("entity_id", run.id)),
        actor=actor,
        correlation_id=run.correlation_id,
        model_name=details.get("model_name"),
        model_version=details.get("model_version"),
        prompt_hash=details.get("prompt_hash"),
        retrieval_hash=details.get("retrieval_hash"),
        threshold_status=details.get("threshold_status"),
        policy_decision=details.get("policy_decision"),
        details=details,
    )
    session.add(record)
    session.flush()
    return record

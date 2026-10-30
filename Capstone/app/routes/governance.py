from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import current_user
from app.db import get_session
from app.models import GovernanceRecord


router = APIRouter(prefix="/api/governance", tags=["governance"])


@router.get("")
def list_governance(run_id: str, request: Request, session: Session = Depends(get_session)) -> list[dict]:
    if current_user(request) is None:
        raise HTTPException(status_code=401, detail="Login required")
    records = session.execute(
        select(GovernanceRecord)
        .where(GovernanceRecord.run_id == run_id)
        .order_by(GovernanceRecord.created_at.asc())
    ).scalars()
    return [
        {
            "event_type": record.event_type,
            "entity_type": record.entity_type,
            "entity_id": record.entity_id,
            "actor": record.actor,
            "correlation_id": record.correlation_id,
            "model_name": record.model_name,
            "model_version": record.model_version,
            "prompt_hash": record.prompt_hash,
            "retrieval_hash": record.retrieval_hash,
            "threshold_status": record.threshold_status,
            "policy_decision": record.policy_decision,
            "details": record.details,
        }
        for record in records
    ]

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import ApprovalRequest
from app.rca_agent import decide_approval


router = APIRouter(prefix="/api/approvals", tags=["approvals"])


def _decide(approval_id: str, decision: str, session: Session) -> dict:
    try:
        approval = decide_approval(session, approval_id, actor="admin", decision=decision)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "approval_id": approval.id,
        "status": approval.status,
        "decided_by": approval.decided_by,
        "remediation": approval.remediation_result,
    }


@router.get("")
def list_approvals(status: str = "pending", session: Session = Depends(get_session)) -> list[dict]:
    approvals = session.execute(
        select(ApprovalRequest).where(ApprovalRequest.status == status)
    ).scalars()
    return [
        {
            "approval_id": approval.id,
            "finding_id": approval.finding_id,
            "status": approval.status,
            "requested_action": approval.requested_action,
        }
        for approval in approvals
    ]


@router.post("/{approval_id}/approve")
def approve(approval_id: str, session: Session = Depends(get_session)) -> dict:
    return _decide(approval_id, "approved", session)


@router.post("/{approval_id}/reject")
def reject(approval_id: str, session: Session = Depends(get_session)) -> dict:
    return _decide(approval_id, "rejected", session)

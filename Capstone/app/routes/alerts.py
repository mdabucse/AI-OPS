from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.alerting import send_alert
from app.auth import current_user
from app.db import get_session
from app.models import AlertEvent


router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.post("/{run_id}/send")
def send_run_alert(run_id: str, request: Request, session: Session = Depends(get_session)) -> dict:
    if current_user(request) is None:
        raise HTTPException(status_code=401, detail="Login required")
    alert = send_alert(session, run_id)
    return {"alert_id": alert.id, "status": alert.status, "channel": alert.channel, "error": alert.error}


@router.get("")
def list_alerts(run_id: str, request: Request, session: Session = Depends(get_session)) -> list[dict]:
    if current_user(request) is None:
        raise HTTPException(status_code=401, detail="Login required")
    alerts = session.execute(
        select(AlertEvent).where(AlertEvent.run_id == run_id).order_by(AlertEvent.created_at.desc())
    ).scalars()
    return [
        {"alert_id": alert.id, "channel": alert.channel, "status": alert.status, "error": alert.error}
        for alert in alerts
    ]

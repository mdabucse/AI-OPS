from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import create_audit_event
from app.governance import record_governance_event
from app.models import AlertEvent, AnomalyEvent, SimulationRun, ThresholdEvaluation


def _payload(run: SimulationRun, anomaly: AnomalyEvent | None, threshold: ThresholdEvaluation | None) -> dict:
    score = anomaly.score if anomaly else None
    observed = anomaly.observed_value if anomaly else None
    threshold_value = threshold.threshold_value if threshold else None
    return {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "summary": "AIOps RCA alert",
        "themeColor": "D13438",
        "title": "AIOps RCA alert: login latency anomaly",
        "text": (
            f"Run {run.id} detected login P95 {observed}s, "
            f"dynamic threshold {threshold_value}s, anomaly score {score}."
        ),
    }


def send_alert(session: Session, run_id: str, channel: str = "teams") -> AlertEvent:
    run = session.execute(select(SimulationRun).where(SimulationRun.id == run_id)).scalar_one()
    anomaly = session.execute(
        select(AnomalyEvent).where(AnomalyEvent.run_id == run.id).order_by(AnomalyEvent.created_at.desc())
    ).scalars().first()
    threshold = session.execute(
        select(ThresholdEvaluation)
        .where(ThresholdEvaluation.run_id == run.id)
        .order_by(ThresholdEvaluation.created_at.desc())
    ).scalars().first()
    payload = _payload(run, anomaly, threshold)
    alert = AlertEvent(
        run_id=run.id,
        channel=channel,
        subject=payload["title"],
        payload=payload,
        status="simulated",
    )
    if channel == "teams" and settings.teams_webhook_url:
        request = Request(
            settings.teams_webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=5) as response:
                if not 200 <= response.status < 300:
                    raise OSError(f"Teams webhook returned HTTP {response.status}")
            alert.status = "sent"
            alert.sent_at = datetime.now(timezone.utc)
        except Exception as exc:
            alert.status = "failed"
            alert.error = str(exc)
    else:
        alert.sent_at = datetime.now(timezone.utc)

    session.add(alert)
    session.flush()
    create_audit_event(
        session,
        event_type="alert.sent" if alert.status in {"sent", "simulated"} else "alert.failed",
        actor="system",
        correlation_id=run.correlation_id,
        details={
            "run_id": run.id,
            "alert_id": alert.id,
            "channel": alert.channel,
            "status": alert.status,
            "error": alert.error,
        },
    )
    record_governance_event(
        session,
        run.id,
        event_type="alert.created",
        actor="system",
        details={
            "entity_type": "alert",
            "entity_id": str(alert.id),
            "model_name": anomaly.model_name if anomaly else None,
            "model_version": anomaly.model_version if anomaly else None,
            "threshold_status": threshold.status if threshold else None,
            "policy_decision": "notification_required",
        },
    )
    session.commit()
    session.refresh(alert)
    return alert

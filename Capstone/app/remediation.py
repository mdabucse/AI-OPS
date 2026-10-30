from __future__ import annotations

from datetime import datetime, timezone

from app.db import create_audit_event
from app.governance import record_governance_event
from app.models import ApprovalRequest, TelemetryEvent
from app.pool_state import EXPANDED_POOL_SIZE, get_pool_size, set_pool_size


def apply_remediation(session, approval: ApprovalRequest, actor: str) -> dict:
    """Apply a safe, simulated pool-capacity change after human approval."""
    run = approval.finding.run
    timestamp = datetime.now(timezone.utc)
    previous_pool_size = get_pool_size(session)
    set_pool_size(session, EXPANDED_POOL_SIZE)
    changes = {
        "p95_seconds": 0.12,
        "active_connections": 4,
        "waiting_requests": 0,
        "pool_max_before": previous_pool_size,
        "pool_max_after": EXPANDED_POOL_SIZE,
        "message": "Simulated database pool capacity increase applied",
    }
    session.add_all(
        [
            TelemetryEvent(
                run_id=run.id,
                metric_name="login_p95_latency_after_remediation",
                value=changes["p95_seconds"],
                unit="seconds",
                timestamp=timestamp,
            ),
            TelemetryEvent(
                run_id=run.id,
                metric_name="db_active_connections_after_remediation",
                value=changes["active_connections"],
                unit="connections",
                timestamp=timestamp,
            ),
            TelemetryEvent(
                run_id=run.id,
                metric_name="db_pool_max_after_remediation",
                value=changes["pool_max_after"],
                unit="connections",
                timestamp=timestamp,
            ),
            TelemetryEvent(
                run_id=run.id,
                metric_name="waiting_requests_after_remediation",
                value=changes["waiting_requests"],
                unit="requests",
                timestamp=timestamp,
            ),
        ]
    )
    result = {"status": "applied", "changes": changes}
    create_audit_event(
        session,
        event_type="remediation.applied",
        actor=actor,
        correlation_id=run.correlation_id,
        details={"approval_id": approval.id, "run_id": run.id, **result},
    )
    record_governance_event(
        session,
        run.id,
        event_type="remediation.applied",
        actor=actor,
        details={
            "entity_type": "remediation",
            "entity_id": approval.id,
            "policy_decision": "approved",
        },
    )
    return result


def remediation_not_applied() -> dict:
    return {"status": "not_applied", "message": "No system state was changed"}

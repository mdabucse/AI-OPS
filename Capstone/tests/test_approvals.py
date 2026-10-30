import pytest
from sqlalchemy.exc import NoResultFound

from app.db import SessionLocal, init_db
from app.models import ApprovalRequest
from app.rca_agent import create_approval_request, create_rca_finding, decide_approval
from app.simulation import start_login_scenario


def test_rca_finding_contains_pool_diagnosis_and_evidence():
    init_db()

    with SessionLocal() as session:
        run = start_login_scenario(session, actor="admin")
        finding = create_rca_finding(session, run.id, actor="admin")

        assert "connection pool" in finding.root_cause.lower()
        assert any("1.35" in item for item in finding.evidence)
        assert any("20" in item for item in finding.evidence)
        assert finding.model_name
        assert finding.context_hash
        assert finding.retrieved_context[0]["document_id"] == "runbook-db-pool-saturation"
        assert 0 < finding.confidence <= 1


def test_approval_can_be_approved_only_once_and_is_audited():
    init_db()

    with SessionLocal() as session:
        run = start_login_scenario(session, actor="admin")
        finding = create_rca_finding(session, run.id, actor="admin")
        approval = create_approval_request(session, finding.id, actor="admin")

        decided = decide_approval(session, approval.id, actor="admin", decision="approved")
        assert decided.status == "approved"
        assert decided.decided_by == "admin"

        with pytest.raises(ValueError, match="already decided"):
            decide_approval(session, approval.id, actor="admin", decision="rejected")


def test_approval_can_be_rejected():
    init_db()

    with SessionLocal() as session:
        run = start_login_scenario(session, actor="admin")
        finding = create_rca_finding(session, run.id, actor="admin")
        approval = create_approval_request(session, finding.id, actor="admin")
        rejected = decide_approval(session, approval.id, actor="admin", decision="rejected")

        assert rejected.status == "rejected"
        assert session.query(ApprovalRequest).filter_by(id=approval.id, status="rejected").one()

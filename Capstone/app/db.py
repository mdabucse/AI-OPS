from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models import AuditEvent, Base


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    # Keep the local training database forward-compatible after model changes.
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE rca_findings "
                "ADD COLUMN IF NOT EXISTS context_hash VARCHAR(64) NOT NULL DEFAULT ''"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE approval_requests "
                "ADD COLUMN IF NOT EXISTS remediation_result JSON"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE rca_findings "
                "ADD COLUMN IF NOT EXISTS retrieved_context JSON NOT NULL DEFAULT '[]'"
            )
        )


def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def create_audit_event(
    session: Session,
    event_type: str,
    actor: str,
    correlation_id: str,
    details: dict,
) -> AuditEvent:
    event = AuditEvent(
        actor=actor,
        event_type=event_type,
        correlation_id=correlation_id,
        details=details,
    )
    session.add(event)
    session.flush()
    return event

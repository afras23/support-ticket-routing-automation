"""
Audit service.

Owns the database engine and session factory. Persists the full pipeline
result for every processed ticket.

All database access goes through this module — no raw SQL or session
creation anywhere else in the application.
"""

import logging
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.models.ticket import Base, TicketLog
from app.schemas.ticket import AutomationResult, ClassificationResult, RoutingDecision, TicketRequest

logger = logging.getLogger(__name__)


def _build_engine():
    url = settings.database_url
    kwargs: dict = {"connect_args": {"check_same_thread": False}}
    # In-memory SQLite: force all connections to share a single in-memory DB
    # so that tables created at startup are visible to subsequent requests.
    if ":memory:" in url:
        kwargs["poolclass"] = StaticPool
    return create_engine(url, **kwargs)


engine = _build_engine()

Base.metadata.create_all(bind=engine)

_SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """
    Yield a database session and ensure it is closed after the request.

    Use as a FastAPI dependency: db: Session = Depends(get_db)
    """
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def log_ticket(
    ticket: TicketRequest,
    classification: ClassificationResult,
    routing: RoutingDecision,
    automation: AutomationResult,
    db: Session,
) -> TicketLog:
    """
    Persist the full pipeline result to the audit log.

    Args:
        ticket: Original inbound request.
        classification: Classification + scored confidence.
        routing: Routing decision (queue + reason).
        automation: Auto-resolution outcome.
        db: Active database session.

    Returns:
        The persisted TicketLog record (with id populated).
    """
    entry = TicketLog(
        subject=ticket.subject,
        body=ticket.body,
        customer_email=ticket.customer_email,
        category=classification.category,
        urgency=classification.urgency,
        confidence=classification.confidence,
        routing_queue=routing.queue,
        routing_reason=routing.reason,
        automation_resolved=automation.resolved,
        automation_reason=automation.reason,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    logger.info(
        "Ticket logged to audit",
        extra={
            "ticket_id": entry.id,
            "category": entry.category,
            "queue": entry.routing_queue,
            "resolved": entry.automation_resolved,
        },
    )

    return entry

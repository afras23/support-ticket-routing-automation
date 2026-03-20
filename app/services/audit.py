"""
Audit service.

Owns the database engine and session factory. Persists ticket processing
records and provides the get_db dependency for FastAPI routes.

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
from app.schemas.ticket import ClassifiedTicket

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
    classified: ClassifiedTicket,
    routed_to: str,
    db: Session,
) -> TicketLog:
    """
    Persist a classified ticket to the audit log.

    Args:
        classified: Classification result.
        routed_to: Channel the ticket was routed to.
        db: Active database session.

    Returns:
        The persisted TicketLog record (with id populated).
    """
    entry = TicketLog(
        category=classified.category,
        urgency=classified.urgency,
        sentiment=classified.sentiment,
        product_area=classified.product_area,
        confidence=classified.confidence,
        summary=classified.summary,
        routed_to=routed_to,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    logger.info(
        "Ticket logged to audit",
        extra={
            "ticket_id": entry.id,
            "category": entry.category,
            "routed_to": routed_to,
        },
    )

    return entry

"""
Automation service.

Orchestrates the full ticket processing pipeline:
  ingestion → classification → routing → audit → metrics

This is the only module that coordinates across services. Route handlers
call process_ticket() and receive a TicketResponse — they don't know how
classification or routing work internally.
"""

import logging

from sqlalchemy.orm import Session

from app.core.metrics import metrics
from app.schemas.ticket import TicketRequest, TicketResponse
from app.services import audit, classification, ingestion, routing

logger = logging.getLogger(__name__)


def process_ticket(ticket: TicketRequest, db: Session) -> TicketResponse:
    """
    Run a ticket through the full processing pipeline.

    Args:
        ticket: Validated inbound ticket.
        db: Database session for audit logging.

    Returns:
        TicketResponse containing routing decision and classification.
    """
    subject, body = ingestion.ingest(ticket)
    classified = classification.classify(subject, body)
    channel = routing.route(classified.category)
    audit_entry = audit.log_ticket(classified, channel, db)

    metrics.record_ticket(classified.category, channel)

    logger.info(
        "Ticket processing complete",
        extra={
            "ticket_id": audit_entry.id,
            "category": classified.category,
            "routed_to": channel,
            "confidence": classified.confidence,
        },
    )

    return TicketResponse(routed_to=channel, classification=classified)

"""
Ticket ingestion service.

Validates and preprocesses raw inbound ticket data before classification.
Keeps sanitisation logic out of both the route handler and the classifier.
"""

import logging

from app.schemas.ticket import TicketRequest

logger = logging.getLogger(__name__)


def ingest(ticket: TicketRequest) -> tuple[str, str]:
    """
    Preprocess a ticket into a normalised (subject, body) pair.

    Strips surrounding whitespace. Future work: HTML stripping, PII
    detection, or encoding normalisation can be added here without
    touching the classifier.

    Args:
        ticket: Validated inbound ticket.

    Returns:
        Tuple of (subject, body) ready for classification.
    """
    subject = ticket.subject.strip()
    body = ticket.body.strip()

    logger.info(
        "Ticket ingested",
        extra={
            "customer_email": ticket.customer_email,
            "subject_length": len(subject),
            "body_length": len(body),
        },
    )

    return subject, body

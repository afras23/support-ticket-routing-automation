"""
Orchestrator.

Single entry point for the full ticket decision pipeline:

  ingestion → classification → confidence scoring → routing → auto-resolution → audit

Route handlers call process_ticket() and receive a PipelineResult.
They don't know how any individual stage works.
"""

import logging

from sqlalchemy.orm import Session

from app.core.metrics import metrics
from app.schemas.ticket import PipelineResult, TicketRequest
from app.services import audit, auto_resolve, classification, confidence, ingestion, routing

logger = logging.getLogger(__name__)


def process_ticket(ticket: TicketRequest, db: Session) -> PipelineResult:
    """
    Run a ticket through the full decision pipeline.

    Pipeline:
      1. Ingest      — normalise raw input
      2. Classify    — category + urgency + base confidence (via ai_client)
      3. Score       — apply rule adjustments to confidence
      4. Route       — decide queue based on confidence + urgency + category
      5. Auto-resolve — attempt resolution for simple, high-confidence cases
      6. Audit       — persist all decisions to the database
      7. Metrics     — update in-memory counters

    Args:
        ticket: Validated inbound ticket.
        db: Database session for audit logging.

    Returns:
        PipelineResult containing all stage outputs.
    """
    # 1. Ingest
    subject, body = ingestion.ingest(ticket)

    # 2. Classify (base confidence)
    raw = classification.classify(subject, body)

    # 3. Score confidence (apply rule adjustments)
    adjusted_confidence = confidence.score(subject, body, raw.confidence)
    classified = raw.model_copy(update={"confidence": adjusted_confidence})

    # 4. Route
    routing_decision = routing.route(classified)

    # 5. Auto-resolve
    automation_result = auto_resolve.automate(classified, subject, body)

    # 6. Audit
    audit_entry = audit.log_ticket(ticket, classified, routing_decision, automation_result, db)

    # 7. Metrics
    metrics.record_ticket(classified.category, routing_decision.queue)

    logger.info(
        "Pipeline complete",
        extra={
            "ticket_id": audit_entry.id,
            "category": classified.category,
            "urgency": classified.urgency,
            "confidence": classified.confidence,
            "queue": routing_decision.queue,
            "resolved": automation_result.resolved,
        },
    )

    return PipelineResult(
        ticket_id=audit_entry.id,
        classification=classified,
        routing=routing_decision,
        automation=automation_result,
    )

"""
Ticket routing service.

Routes a classified ticket to the appropriate queue based on three signals
evaluated in priority order:

  1. Confidence — low confidence goes to manual review regardless of category.
  2. Urgency   — high urgency escalates regardless of category.
  3. Category  — determines the team queue for normal-confidence/urgency tickets.

Available queues: escalation | manual_review | finance | support | general
"""

import logging

from app.schemas.ticket import ClassificationResult, RoutingDecision

logger = logging.getLogger(__name__)

# Confidence below this threshold means we're not certain enough to auto-route.
CONFIDENCE_MANUAL_REVIEW_THRESHOLD = 0.60


def route(classification: ClassificationResult) -> RoutingDecision:
    """
    Determine the queue and routing reason for a classified ticket.

    Args:
        classification: Output of classification + confidence scoring.

    Returns:
        RoutingDecision with target queue and human-readable reason.
    """
    # 1. Low confidence → manual review (we can't trust the category).
    if classification.confidence < CONFIDENCE_MANUAL_REVIEW_THRESHOLD:
        decision = RoutingDecision(
            queue="manual_review",
            reason=f"Confidence too low for auto-routing ({classification.confidence:.2f})",
        )

    # 2. High urgency → escalation (time-sensitive, needs immediate attention).
    elif classification.urgency == "high":
        decision = RoutingDecision(
            queue="escalation",
            reason="High urgency — requires immediate attention",
        )

    # 3. Category-based routing.
    elif classification.category == "billing":
        decision = RoutingDecision(queue="finance", reason="Billing or payment inquiry")

    elif classification.category == "technical":
        decision = RoutingDecision(queue="support", reason="Technical support request")

    else:
        decision = RoutingDecision(queue="general", reason="General inquiry")

    logger.info(
        "Ticket routed",
        extra={
            "queue": decision.queue,
            "reason": decision.reason,
            "category": classification.category,
            "urgency": classification.urgency,
            "confidence": classification.confidence,
        },
    )

    return decision

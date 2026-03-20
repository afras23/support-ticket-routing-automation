"""
Ticket classification service.

Thin wrapper around an AIClient. The default client is the deterministic
rule-based classifier — no external dependencies required.

To swap in an LLM, pass ai_client= to classify():

    from app.ai.client import ClaudeClassifier
    result = classification.classify(subject, body, ai_client=ClaudeClassifier())
"""

import logging

from app.ai.client import AIClient, default_classifier
from app.schemas.ticket import ClassificationResult

logger = logging.getLogger(__name__)


def classify(
    subject: str,
    body: str,
    *,
    ai_client: AIClient | None = None,
) -> ClassificationResult:
    """
    Classify a ticket into category, urgency, and base confidence.

    The confidence returned here is the *base* value from the classifier.
    The confidence scorer (app/services/confidence.py) applies rule-based
    adjustments before routing decisions are made.

    Args:
        subject: Ticket subject line.
        body: Ticket body text.
        ai_client: Classifier to use. Defaults to RuleBasedClassifier.

    Returns:
        ClassificationResult with category, urgency, and base confidence.
    """
    client: AIClient = ai_client or default_classifier
    result = client.classify(subject, body)

    logger.info(
        "Ticket classified",
        extra={
            "category": result.category,
            "urgency": result.urgency,
            "base_confidence": result.confidence,
        },
    )

    return result

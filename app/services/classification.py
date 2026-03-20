"""
Ticket classification service.

Rule-based classifier using keyword matching. All classification logic
lives here and is independently testable.

Architecture note: to upgrade to LLM-based classification, replace the
private _detect_* helpers with an AI call — the public classify() interface
stays the same and nothing else in the codebase changes.
"""

import logging

from app.config import settings
from app.schemas.ticket import ClassifiedTicket, Sentiment, TicketCategory, Urgency

logger = logging.getLogger(__name__)

# Keyword lists drive category detection. Order matters: first match wins.
_CATEGORY_KEYWORDS: dict[TicketCategory, list[str]] = {
    "bug": ["crash", "error", "bug", "broken", "failure", "exception", "not working"],
    "feature_request": ["feature", "request", "add", "would be nice", "suggestion", "improve"],
    "billing": ["invoice", "billing", "payment", "charge", "refund", "subscription", "price"],
    "technical_question": [],  # fallback — matched when nothing else fits
}

_URGENCY_KEYWORDS = ["urgent", "asap", "immediately", "critical", "emergency"]
_NEGATIVE_KEYWORDS = ["angry", "frustrated", "bad", "terrible", "awful", "unacceptable", "disappointed"]
_POSITIVE_KEYWORDS = ["great", "happy", "love", "thanks", "appreciate", "excellent"]


def _detect_category(text: str) -> TicketCategory:
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return category
    return "technical_question"


def _detect_urgency(text: str) -> Urgency:
    return "high" if any(kw in text for kw in _URGENCY_KEYWORDS) else "medium"


def _detect_sentiment(text: str) -> Sentiment:
    if any(kw in text for kw in _NEGATIVE_KEYWORDS):
        return "negative"
    if any(kw in text for kw in _POSITIVE_KEYWORDS):
        return "positive"
    return "neutral"


def classify(subject: str, body: str) -> ClassifiedTicket:
    """
    Classify a support ticket by category, urgency, and sentiment.

    Args:
        subject: Ticket subject line.
        body: Ticket body text.

    Returns:
        ClassifiedTicket with all metadata populated.
    """
    text = f"{subject} {body}".lower()

    category = _detect_category(text)
    urgency = _detect_urgency(text)
    sentiment = _detect_sentiment(text)
    summary = body[:180] + "..." if len(body) > 180 else body

    result = ClassifiedTicket(
        category=category,
        urgency=urgency,
        sentiment=sentiment,
        product_area="core-platform",
        confidence=settings.confidence_default,
        summary=summary,
    )

    logger.info(
        "Ticket classified",
        extra={
            "category": category,
            "urgency": urgency,
            "sentiment": sentiment,
            "confidence": result.confidence,
        },
    )

    return result

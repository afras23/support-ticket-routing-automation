"""
AI client abstraction for ticket classification.

Defines the AIClient protocol so any classifier — rule-based, LLM-backed,
or test mock — can be swapped without touching the rest of the pipeline.

The RuleBasedClassifier is the deterministic default. To swap in an LLM:

    class ClaudeClassifier:
        def classify(self, subject: str, body: str) -> ClassificationResult:
            # call Anthropic API here
            ...

    classification.classify(subject, body, ai_client=ClaudeClassifier())
"""

import logging
from typing import Protocol, runtime_checkable

from app.schemas.ticket import ClassificationResult, TicketCategory, Urgency

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Protocol — the contract every classifier must satisfy
# ---------------------------------------------------------------------------

@runtime_checkable
class AIClient(Protocol):
    """Interface for ticket classifiers.  Accepts raw text, returns structured result."""

    def classify(self, subject: str, body: str) -> ClassificationResult:
        ...


# ---------------------------------------------------------------------------
# Keyword tables for the rule-based fallback
# ---------------------------------------------------------------------------

_CATEGORY_KEYWORDS: dict[TicketCategory, list[str]] = {
    "billing": [
        "invoice", "billing", "payment", "charge", "refund",
        "subscription", "price", "cost", "receipt", "overcharged", "fee",
    ],
    "technical": [
        "crash", "error", "bug", "broken", "failure", "exception",
        "not working", "login", "password", "access", "connect",
        "install", "configure", "sso", "integration", "api", "outage",
    ],
    "general": [],  # explicit fallback
}

_HIGH_URGENCY_KEYWORDS = [
    "urgent", "asap", "immediately", "critical", "emergency",
    "outage", "down", "cannot access", "can't access",
]

_LOW_URGENCY_KEYWORDS = [
    "question", "wondering", "curious", "when will", "suggestion",
    "feedback", "how to", "information", "general inquiry",
]


def _detect_category(text: str) -> TicketCategory:
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return category
    return "general"


def _detect_urgency(text: str) -> Urgency:
    if any(kw in text for kw in _HIGH_URGENCY_KEYWORDS):
        return "high"
    if any(kw in text for kw in _LOW_URGENCY_KEYWORDS):
        return "low"
    return "medium"


def _base_confidence(category: TicketCategory, text: str) -> float:
    """
    Base confidence from the rule-based classifier.

    Driven by how many category keywords were matched — more matches
    means the classifier is more certain. Falls back to 0.60 for the
    general/fallback category.
    """
    keywords = _CATEGORY_KEYWORDS.get(category, [])
    match_count = sum(1 for kw in keywords if kw in text)

    if match_count >= 3:
        return 0.90
    if match_count == 2:
        return 0.80
    if match_count == 1:
        return 0.72
    return 0.60  # fallback / general — inherently ambiguous


# ---------------------------------------------------------------------------
# Default implementation — no external dependencies
# ---------------------------------------------------------------------------

class RuleBasedClassifier:
    """
    Deterministic keyword-matching classifier.

    Suitable as a production fallback or for environments where no
    LLM API key is available.  All behaviour is predictable and testable.
    """

    def classify(self, subject: str, body: str) -> ClassificationResult:
        """
        Classify a ticket by scanning for keyword patterns.

        Args:
            subject: Ticket subject line.
            body: Ticket body text.

        Returns:
            ClassificationResult with category, urgency, and base confidence.
        """
        text = f"{subject} {body}".lower()
        category = _detect_category(text)
        urgency = _detect_urgency(text)
        confidence = _base_confidence(category, text)

        logger.debug(
            "Rule-based classification complete",
            extra={
                "category": category,
                "urgency": urgency,
                "base_confidence": confidence,
            },
        )

        return ClassificationResult(
            category=category,
            urgency=urgency,
            confidence=confidence,
        )


# Module-level default — used when no ai_client is passed to classify().
default_classifier: AIClient = RuleBasedClassifier()

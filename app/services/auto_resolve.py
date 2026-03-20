"""
Auto-resolution service.

Attempts to automatically resolve a ticket without human intervention.
Auto-resolution is intentionally conservative: it only fires when ALL
three conditions are met:

  1. Confidence exceeds the threshold (we're sure about the classification).
  2. Category is "general" (billing and technical issues require human review).
  3. The ticket matches a known auto-resolvable pattern (password reset, FAQ, etc.).

This avoids false positives — it is better to escalate than to silently
drop a genuine issue.
"""

import logging

from app.schemas.ticket import AutomationResult, ClassificationResult

logger = logging.getLogger(__name__)

# Minimum confidence required to attempt auto-resolution.
CONFIDENCE_AUTO_RESOLVE_THRESHOLD = 0.85

# Patterns that indicate a ticket can be auto-resolved.
# These are simple substring matches — replace with an LLM intent classifier
# if more nuance is needed.
_AUTO_RESOLVE_PATTERNS = [
    "password reset",
    "reset my password",
    "forgot password",
    "how to",
    "how do i",
    "where can i",
    "what is",
    "when does",
    "getting started",
]


def automate(
    classification: ClassificationResult,
    subject: str,
    body: str,
) -> AutomationResult:
    """
    Determine whether a ticket can be auto-resolved.

    Args:
        classification: Classified + scored ticket.
        subject: Ticket subject line.
        body: Ticket body text.

    Returns:
        AutomationResult indicating resolved status and reason.
    """
    # Gate 1: confidence must be high enough to act without human review.
    if classification.confidence < CONFIDENCE_AUTO_RESOLVE_THRESHOLD:
        result = AutomationResult(
            resolved=False,
            reason=(
                f"Confidence {classification.confidence:.2f} is below "
                f"auto-resolve threshold {CONFIDENCE_AUTO_RESOLVE_THRESHOLD}"
            ),
        )

    # Gate 2: only general category tickets are eligible.
    elif classification.category != "general":
        result = AutomationResult(
            resolved=False,
            reason=f"Category '{classification.category}' requires human review",
        )

    else:
        # Gate 3: check for known auto-resolvable patterns.
        text = f"{subject} {body}".lower()
        matched_pattern = next(
            (pattern for pattern in _AUTO_RESOLVE_PATTERNS if pattern in text),
            None,
        )

        if matched_pattern:
            result = AutomationResult(
                resolved=True,
                reason=f"Matched auto-resolve pattern: '{matched_pattern}'",
            )
        else:
            result = AutomationResult(
                resolved=False,
                reason="No auto-resolve pattern matched",
            )

    logger.info(
        "Auto-resolution evaluated",
        extra={
            "resolved": result.resolved,
            "reason": result.reason,
            "category": classification.category,
            "confidence": classification.confidence,
        },
    )

    return result

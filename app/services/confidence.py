"""
Confidence scoring service.

Takes the base confidence produced by the classifier and applies
rule-based adjustments. Keeping this separate from classification
means the two concerns can be tuned and tested independently.

Adjustment rules:
  - Short ticket body → penalty  (less context = less certainty)
  - Known signal keywords present → boost  (strong domain indicators)
  - Result is always clamped to [0.0, 1.0]
"""

import logging

logger = logging.getLogger(__name__)

# Ticket body shorter than this is considered ambiguous.
_SHORT_BODY_CHARS = 50
_SHORT_BODY_PENALTY = 0.15

# Keywords that signal strong domain intent — presence boosts certainty.
_SIGNAL_KEYWORDS = [
    "urgent", "asap", "crash", "down", "outage",
    "payment", "invoice", "refund", "charge",
    "password", "reset", "cannot login", "can't login",
    "error", "exception", "broken",
]
_KEYWORD_BOOST_PER_MATCH = 0.08
_MAX_KEYWORD_BOOST = 0.20


def score(subject: str, body: str, base_confidence: float) -> float:
    """
    Return an adjusted confidence score for a ticket.

    Args:
        subject: Ticket subject line.
        body: Ticket body text.
        base_confidence: Initial confidence from the classifier (0.0–1.0).

    Returns:
        Adjusted confidence clamped to [0.0, 1.0].
    """
    adjusted = base_confidence
    text = f"{subject} {body}".lower()

    # Penalty: short body provides little context.
    if len(body.strip()) < _SHORT_BODY_CHARS:
        adjusted -= _SHORT_BODY_PENALTY
        logger.debug(
            "Short body penalty applied",
            extra={"body_length": len(body.strip()), "penalty": _SHORT_BODY_PENALTY},
        )

    # Boost: known signal keywords increase certainty.
    match_count = sum(1 for kw in _SIGNAL_KEYWORDS if kw in text)
    if match_count > 0:
        boost = min(match_count * _KEYWORD_BOOST_PER_MATCH, _MAX_KEYWORD_BOOST)
        adjusted += boost
        logger.debug(
            "Keyword boost applied",
            extra={"keyword_matches": match_count, "boost": boost},
        )

    final = max(0.0, min(1.0, adjusted))

    logger.info(
        "Confidence scored",
        extra={
            "base": base_confidence,
            "final": final,
            "delta": round(final - base_confidence, 4),
        },
    )

    return final

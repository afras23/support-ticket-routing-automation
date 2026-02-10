import re
from app.models import ClassifiedTicket

def classify_ticket(subject: str, body: str) -> ClassifiedTicket:
    text = f"{subject} {body}".lower()

    if any(w in text for w in ["crash", "error", "bug", "broken"]):
        category = "bug"
    elif any(w in text for w in ["feature", "request", "add"]):
        category = "feature_request"
    elif any(w in text for w in ["invoice", "billing", "payment"]):
        category = "billing"
    else:
        category = "technical_question"

    urgency = "high" if "urgent" in text or "asap" in text else "medium"
    sentiment = "negative" if any(w in text for w in ["angry", "frustrated", "bad"]) else "neutral"

    summary = body[:180] + "..." if len(body) > 180 else body

    return ClassifiedTicket(
        category=category,
        urgency=urgency,
        sentiment=sentiment,
        product_area="core-platform",
        confidence=0.82,
        summary=summary
    )

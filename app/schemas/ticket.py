"""
Pydantic schemas for ticket request and response contracts.

These are the API-boundary types. The SQLAlchemy model (app/models/ticket.py)
is kept separate — schemas are for validation and serialisation only.
"""

from typing import Literal

from pydantic import BaseModel, Field

TicketCategory = Literal["bug", "feature_request", "billing", "technical_question"]
Urgency = Literal["low", "medium", "high"]
Sentiment = Literal["negative", "neutral", "positive"]


class TicketRequest(BaseModel):
    """Inbound ticket submitted by a customer or webhook."""

    subject: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1, max_length=10_000)
    customer_email: str = Field(..., description="Submitting customer's email address")


class ClassifiedTicket(BaseModel):
    """Ticket enriched with classification metadata."""

    category: TicketCategory
    urgency: Urgency
    sentiment: Sentiment
    product_area: str
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str


class TicketResponse(BaseModel):
    """API response returned after a ticket is processed."""

    routed_to: str
    classification: ClassifiedTicket

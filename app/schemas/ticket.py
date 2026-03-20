"""
Pydantic schemas for ticket request, pipeline stages, and response contracts.

These are the API-boundary and inter-service types. The SQLAlchemy ORM model
(app/models/ticket.py) is kept separate.
"""

from typing import Literal

from pydantic import BaseModel, Field

TicketCategory = Literal["billing", "technical", "general"]
Urgency = Literal["low", "medium", "high"]


class TicketRequest(BaseModel):
    """Inbound ticket submitted by a customer or webhook."""

    subject: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1, max_length=10_000)
    customer_email: str = Field(..., description="Submitting customer's email address")


class ClassificationResult(BaseModel):
    """Output of the classification step (base confidence, before scoring)."""

    category: TicketCategory
    urgency: Urgency
    confidence: float = Field(ge=0.0, le=1.0)


class RoutingDecision(BaseModel):
    """Where to send the ticket and why."""

    queue: str = Field(
        description=(
            "Target queue: escalation | manual_review | finance | support | general"
        )
    )
    reason: str


class AutomationResult(BaseModel):
    """Outcome of the auto-resolution attempt."""

    resolved: bool
    reason: str


class PipelineResult(BaseModel):
    """Full result of processing a ticket through the pipeline."""

    ticket_id: int
    classification: ClassificationResult
    routing: RoutingDecision
    automation: AutomationResult

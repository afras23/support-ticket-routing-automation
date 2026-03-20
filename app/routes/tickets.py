"""
Ticket processing endpoint.

Accepts inbound tickets, delegates to the automation service, and returns
the routing decision. No business logic lives here.
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas.ticket import TicketRequest, TicketResponse
from app.services.audit import get_db
from app.services.automation import process_ticket

logger = logging.getLogger(__name__)

router = APIRouter(tags=["tickets"])


@router.post("/support-ticket/", response_model=TicketResponse)
def receive_ticket(
    ticket: TicketRequest,
    db: Session = Depends(get_db),
) -> TicketResponse:
    """
    Process an inbound support ticket.

    Classifies the ticket by category, urgency, and sentiment; routes it
    to the appropriate support channel; and persists an audit record.
    """
    return process_ticket(ticket, db)

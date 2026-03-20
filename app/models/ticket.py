"""
SQLAlchemy ORM model for the ticket audit log.

Schema stores the full pipeline result for every processed ticket:
  input fields, classification, routing decision, and automation outcome.

Note: if you already have a tickets.db from a previous schema version,
delete it — create_all() won't migrate existing tables automatically.
"""

from sqlalchemy import Boolean, Column, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class TicketLog(Base):
    """Persistent record of each ticket and every pipeline decision."""

    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Input
    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    customer_email = Column(String(255), nullable=False)

    # Classification
    category = Column(String(64), nullable=False)
    urgency = Column(String(16), nullable=False)
    confidence = Column(Float, nullable=False)

    # Routing
    routing_queue = Column(String(64), nullable=False)
    routing_reason = Column(String(256), nullable=False)

    # Automation
    automation_resolved = Column(Boolean, nullable=False, default=False)
    automation_reason = Column(String(256), nullable=False)

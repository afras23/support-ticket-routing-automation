"""
SQLAlchemy ORM model for the ticket audit log.

This is the database schema. All DB access goes through app/services/audit.py —
no other module imports from here directly except audit.py.
"""

from sqlalchemy import Column, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class TicketLog(Base):
    """Persistent record of each processed ticket."""

    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(64), nullable=False)
    urgency = Column(String(16), nullable=False)
    sentiment = Column(String(16), nullable=False)
    product_area = Column(String(128), nullable=False)
    confidence = Column(Float, nullable=False)
    summary = Column(Text, nullable=False)
    routed_to = Column(String(128), nullable=True)

"""
FastAPI application entry point.

Wires together configuration, logging, and route registration.
No business logic lives here.
"""

from app.config import settings
from app.core.logging import setup_logging

setup_logging(settings.log_level)

from fastapi import FastAPI  # noqa: E402 — import after logging is configured

from app.routes import health, tickets  # noqa: E402

app = FastAPI(
    title="Support Ticket Routing",
    description="Automated support ticket classification, routing, and audit logging.",
    version="1.0.0",
)

app.include_router(health.router)
app.include_router(tickets.router)

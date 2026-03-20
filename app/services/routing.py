"""
Ticket routing service.

Maps classified ticket categories to support channels.
The routing table lives here — no routing logic elsewhere in the app.
"""

import logging

from app.config import settings

logger = logging.getLogger(__name__)

_ROUTING_TABLE: dict[str, str] = {
    "bug": "#support-bugs",
    "feature_request": "#support-features",
    "billing": "#support-billing",
    "technical_question": "#support-tech",
}


def route(category: str) -> str:
    """
    Determine the support channel for a given ticket category.

    Args:
        category: Classified ticket category string.

    Returns:
        Channel name (e.g. '#support-bugs'). Falls back to the
        configured default channel for unknown categories.
    """
    channel = _ROUTING_TABLE.get(category, settings.default_channel)

    logger.info(
        "Ticket routed",
        extra={
            "category": category,
            "channel": channel,
        },
    )

    return channel

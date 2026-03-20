"""
Structured logging configuration.

Sets up structured logging with consistent fields across the application.
Each log entry includes level, logger name, message, and any extra context
fields passed by the caller (ticket_id, category, routing decision, etc.).
"""

import logging
import sys
from typing import Any


class StructuredFormatter(logging.Formatter):
    """Format log records as pipe-separated key=value pairs."""

    # Fields that are internal to LogRecord — excluded from structured output.
    _SKIP = frozenset({
        "name", "msg", "args", "created", "filename", "funcName",
        "levelname", "levelno", "lineno", "message", "module",
        "msecs", "pathname", "process", "processName", "relativeCreated",
        "stack_info", "thread", "threadName", "exc_info", "exc_text",
        "taskName",
    })

    def format(self, record: logging.LogRecord) -> str:
        fields: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in self._SKIP:
                fields[key] = value

        line = " | ".join(f"{k}={v}" for k, v in fields.items())

        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)

        return line


def setup_logging(level: str = "INFO") -> None:
    """Configure application-wide structured logging to stdout."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers.clear()
    root.addHandler(handler)

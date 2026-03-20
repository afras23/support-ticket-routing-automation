"""
Lightweight in-memory metrics.

Tracks request counts and classification/routing distributions.
Suitable for single-process deployments. For multi-process or
multi-instance deployments, replace with Prometheus or similar.
"""

from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class AppMetrics:
    """In-memory counters for operational visibility."""

    request_count: int = 0
    classification_distribution: dict[str, int] = field(
        default_factory=lambda: defaultdict(int)
    )
    routing_distribution: dict[str, int] = field(
        default_factory=lambda: defaultdict(int)
    )

    def record_ticket(self, category: str, channel: str) -> None:
        """Increment counters after a ticket is processed."""
        self.request_count += 1
        self.classification_distribution[category] += 1
        self.routing_distribution[channel] += 1

    def snapshot(self) -> dict:
        """Return a plain-dict snapshot of current metrics."""
        return {
            "request_count": self.request_count,
            "classification_distribution": dict(self.classification_distribution),
            "routing_distribution": dict(self.routing_distribution),
        }


# Module-level singleton shared across the application process.
metrics = AppMetrics()

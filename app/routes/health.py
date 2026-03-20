"""
Health check endpoints.

/health       — liveness: is the process up?
/health/ready — readiness: can it serve traffic? (checks DB)
/metrics      — lightweight operational counters
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.metrics import metrics
from app.services.audit import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Liveness check — confirms the application process is running."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/ready")
def readiness(db: Session = Depends(get_db)) -> dict:
    """
    Readiness check — confirms all dependencies are available.

    Returns 503 if the database cannot be reached.
    """
    checks: dict[str, str] = {}

    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        logger.error("Database readiness check failed", extra={"error": str(exc)})
        checks["database"] = f"error: {exc}"

    all_ok = all(v == "ok" for v in checks.values())
    if not all_ok:
        raise HTTPException(
            status_code=503,
            detail={"status": "degraded", "checks": checks},
        )

    return {"status": "ready", "checks": checks}


@router.get("/metrics")
def get_metrics() -> dict:
    """Return lightweight in-memory operational metrics."""
    return metrics.snapshot()

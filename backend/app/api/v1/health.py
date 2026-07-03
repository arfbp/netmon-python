"""Health check endpoint.

The only endpoint that exists at this step — there's no monitor data
yet to expose. Its job is narrow but important: prove the server is up
AND the configured database is actually reachable, so Step 5+
(WebSocket, then the real monitors) have something to verify against
before more moving parts are added.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.core.deps import DbSessionDep
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    database: str
    timestamp: datetime


@router.get("", response_model=HealthResponse)
async def get_health(session: DbSessionDep) -> HealthResponse:
    """Returns 200 with `status: degraded` (not a 5xx) when the database
    is unreachable — a health check that itself 500s on a DB hiccup is
    a common monitoring anti-pattern; the caller needs to distinguish
    "server process is up but DB is down" from "server process itself
    is broken"."""
    try:
        await session.execute(text("SELECT 1"))
        database_status = "connected"
    except Exception as exc:  # noqa: BLE001 — deliberately broad: any DB failure means "degraded"
        logger.warning("health.database_check_failed", extra={"error": str(exc)})
        database_status = "error"

    return HealthResponse(
        status="ok" if database_status == "connected" else "degraded",
        database=database_status,
        timestamp=datetime.now(UTC),
    )

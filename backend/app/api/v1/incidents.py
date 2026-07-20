"""Incident read endpoints for the dashboard."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.v1.schemas import IncidentResponse
from app.core.deps import DbSessionDep
from app.repositories.incident_repository import IncidentRepository

router = APIRouter(prefix="/incidents", tags=["incidents"])


def _to_response(incident) -> IncidentResponse:  # type: ignore[no-untyped-def]
    context = incident.context or {}
    return IncidentResponse(
        id=incident.id,
        incident_type=incident.incident_type,
        status=incident.status,
        severity=incident.severity,
        triggering_monitor=incident.triggering_monitor,
        started_at=incident.started_at,
        recovered_at=incident.recovered_at,
        summary=incident.summary,
        context=context,
        target=context.get("target"),
    )


@router.get("/active", response_model=list[IncidentResponse])
async def get_active_incidents(session: DbSessionDep) -> list[IncidentResponse]:
    repo = IncidentRepository(session)
    incidents = await repo.get_active()
    return [_to_response(incident) for incident in incidents]


@router.get("/recent", response_model=list[IncidentResponse])
async def get_recent_incidents(
    session: DbSessionDep, limit: int = Query(default=50, ge=1, le=500)
) -> list[IncidentResponse]:
    repo = IncidentRepository(session)
    incidents = await repo.get_recent(limit=limit)
    return [_to_response(incident) for incident in incidents]
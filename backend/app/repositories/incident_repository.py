"""Repository for Incident.

Built alongside the Incident Engine (Step 10), per the repo's pattern:
one repository per concrete model, with query helpers only for the
access patterns the service/API actually need.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import IncidentStatus
from app.models import Incident
from app.repositories.base import BaseRepository


def _incident_target(incident: Incident) -> str | None:
    context = incident.context or {}
    target = context.get("target")
    return str(target) if target is not None else None


class IncidentRepository(BaseRepository[Incident]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Incident)

    async def get_active_for_target(self, target: str) -> Incident | None:
        active = await self.get_active()
        for incident in active:
            if _incident_target(incident) == target:
                return incident
        return None

    async def get_active(self) -> list[Incident]:
        stmt = (
            select(Incident)
            .where(Incident.status.in_([IncidentStatus.STARTED, IncidentStatus.ACTIVE]))
            .order_by(Incident.started_at.desc(), Incident.id.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent(self, limit: int = 50) -> Sequence[Incident]:
        stmt = select(Incident).order_by(Incident.started_at.desc(), Incident.id.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()
"""Repository for PingHistory.

Built now, alongside the Ping Monitor that's the first real consumer —
per Step 3's plan to add per-model repositories when a concrete feature
needs them, rather than speculatively.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PingHistory
from app.repositories.base import BaseRepository


class PingHistoryRepository(BaseRepository[PingHistory]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PingHistory)

    async def get_recent(self, target: str, *, limit: int = 100) -> Sequence[PingHistory]:
        """Most recent rows for one target, newest first — the query
        the dashboard's real-time ping chart (Step 7) will use."""
        stmt = (
            select(PingHistory)
            .where(PingHistory.target == target)
            .order_by(PingHistory.timestamp.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_since(self, target: str, since: datetime) -> Sequence[PingHistory]:
        """Every row for one target from `since` onward, oldest first —
        the shape historical charts (Step 15) need for a time-series
        plot rather than a "most recent N" list."""
        stmt = (
            select(PingHistory)
            .where(PingHistory.target == target, PingHistory.timestamp >= since)
            .order_by(PingHistory.timestamp.asc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def delete_older_than(self, cutoff: datetime) -> int:
        """Supports `DATABASE_RETENTION_DAYS` (Step 2) — deletes rows
        older than the retention cutoff. Returns the number of rows
        deleted. Not yet called anywhere (no retention-sweep job exists
        until a later step wires one up on a schedule); the method
        exists now because it's PingHistory-specific data-access logic,
        the same category of thing as `get_recent`/`get_since`.
        """
        stmt = select(PingHistory).where(PingHistory.timestamp < cutoff)
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        for row in rows:
            await self._session.delete(row)
        await self._session.flush()
        return len(rows)

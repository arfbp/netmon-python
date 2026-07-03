"""Generic base repository.

Contract: this is the ONLY place generic CRUD against `AsyncSession` is
implemented. Per-model repositories (`PingHistoryRepository`,
`IncidentRepository`, ...) subclass `BaseRepository[ModelT]` and add
only the query methods specific to that aggregate (e.g.
`get_active_incidents()`, `get_since(target, timestamp)`) — they never
reimplement `add`/`get_by_id`/`list`.

Per-model repositories themselves are built alongside the services that
first need them (Step 6 onward), rather than speculatively here, so
their specialized methods reflect real query patterns instead of
guessed ones.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Thin wrapper around an `AsyncSession` scoped to one model type.

    Deliberately does NOT commit — callers (services, or the
    `get_db_session()` dependency itself) own the transaction boundary.
    A repository committing internally would make it impossible for a
    service to compose multiple repository calls into one atomic unit
    of work.
    """

    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self._session = session
        self._model = model

    async def add(self, instance: ModelT) -> ModelT:
        self._session.add(instance)
        await self._session.flush()  # assigns PK without committing the transaction
        return instance

    async def get_by_id(self, id_: int) -> ModelT | None:
        return await self._session.get(self._model, id_)

    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[ModelT]:
        stmt = select(self._model).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def delete(self, instance: ModelT) -> None:
        await self._session.delete(instance)
        await self._session.flush()

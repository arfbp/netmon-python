"""Unit tests for BaseRepository — uses an in-memory SQLite session as
the "fake" backing store. Not truly a unit test in the zero-I/O sense
(SQLite in-memory is still I/O), but it's the pragmatic boundary: it
proves BaseRepository's generic CRUD contract without any of Postgres/
file-based SQLite's overhead or state.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.enums import Severity
from app.database.base import Base
from app.models import PingHistory
from app.repositories.base import BaseRepository

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest.fixture
def repo(session: AsyncSession) -> BaseRepository[PingHistory]:
    return BaseRepository(session, PingHistory)


def _make_ping(target: str = "1.1.1.1") -> PingHistory:
    return PingHistory(
        timestamp=datetime.now(UTC),
        target=target,
        latency_ms=10.0,
        is_timeout=False,
        packet_loss_pct=0.0,
        severity=Severity.EXCELLENT,
    )


class TestAdd:
    async def test_add_assigns_primary_key(
        self, repo: BaseRepository[PingHistory]
    ) -> None:
        row = await repo.add(_make_ping())
        assert row.id is not None

    async def test_add_does_not_commit(
        self, repo: BaseRepository[PingHistory], session: AsyncSession
    ) -> None:
        """flush(), not commit() — a service composing multiple
        repository calls must control the transaction boundary."""
        await repo.add(_make_ping())
        assert session.in_transaction()


class TestGetById:
    async def test_returns_none_when_missing(
        self, repo: BaseRepository[PingHistory]
    ) -> None:
        assert await repo.get_by_id(9999) is None

    async def test_returns_the_row(self, repo: BaseRepository[PingHistory]) -> None:
        row = await repo.add(_make_ping())
        fetched = await repo.get_by_id(row.id)
        assert fetched is not None
        assert fetched.target == "1.1.1.1"


class TestList:
    async def test_respects_limit(self, repo: BaseRepository[PingHistory]) -> None:
        for _ in range(5):
            await repo.add(_make_ping())
        results = await repo.list(limit=3)
        assert len(results) == 3

    async def test_respects_offset(self, repo: BaseRepository[PingHistory]) -> None:
        rows = [await repo.add(_make_ping(target=f"target-{i}")) for i in range(5)]
        results = await repo.list(limit=100, offset=2)
        assert len(results) == 3
        assert [r.id for r in results] == [r.id for r in rows[2:]]

    async def test_empty_table_returns_empty_list(
        self, repo: BaseRepository[PingHistory]
    ) -> None:
        assert await repo.list() == []


class TestDelete:
    async def test_delete_removes_row(
        self, repo: BaseRepository[PingHistory]
    ) -> None:
        row = await repo.add(_make_ping())
        row_id = row.id
        await repo.delete(row)
        assert await repo.get_by_id(row_id) is None

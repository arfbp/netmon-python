"""Shared dependency-injection type aliases.

Contract: `api/` routers depend on `SettingsDep`/`DbSessionDep` (never
call `get_settings()`/construct a session directly), so swapping the
provider in tests (`app.dependency_overrides[...] = ...`) affects every
router uniformly.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.database.session import get_db_session

SettingsDep = Annotated[Settings, Depends(get_settings)]


async def _db_session_dependency(settings: SettingsDep) -> AsyncIterator[AsyncSession]:
    """Adapts `database.session.get_db_session` (deliberately
    framework-agnostic, see that module's docstring) into a proper
    FastAPI dependency by resolving `Settings` through `SettingsDep`
    first. This is the one place `database/` and `fastapi` meet."""
    async for session in get_db_session(settings):
        yield session


DbSessionDep = Annotated[AsyncSession, Depends(_db_session_dependency)]

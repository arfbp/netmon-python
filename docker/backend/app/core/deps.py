"""Shared dependency-injection type aliases.

Contract: `api/` routers depend on `SettingsDep`/`DbSessionDep`/
`ConnectionManagerDep` (never call `get_settings()`, construct a
session, or reach into `app.state` directly), so swapping a provider in
tests (`app.dependency_overrides[...] = ...`) affects every router
uniformly.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.database.session import get_db_session
from app.websocket.connection_manager import ConnectionManager

SettingsDep = Annotated[Settings, Depends(get_settings)]


async def _db_session_dependency(settings: SettingsDep) -> AsyncIterator[AsyncSession]:
    """Adapts `database.session.get_db_session` (deliberately
    framework-agnostic, see that module's docstring) into a proper
    FastAPI dependency by resolving `Settings` through `SettingsDep`
    first. This is the one place `database/` and `fastapi` meet."""
    async for session in get_db_session(settings):
        yield session


DbSessionDep = Annotated[AsyncSession, Depends(_db_session_dependency)]


def _connection_manager_dependency(websocket: WebSocket) -> ConnectionManager:
    """The `ConnectionManager` is an app-lifetime singleton (one set of
    connected clients for the whole process), created once in
    `main.create_app` and stored on `app.state` — unlike `DbSessionDep`,
    which constructs a fresh per-request resource. This dependency just
    retrieves the existing instance via the current connection's
    `websocket.app.state`, it doesn't build anything."""
    return websocket.app.state.connection_manager


ConnectionManagerDep = Annotated[ConnectionManager, Depends(_connection_manager_dependency)]

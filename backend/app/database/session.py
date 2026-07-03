"""Async database engine and session lifecycle.

Contract: this module owns the one `AsyncEngine` for the process.
Nothing outside `database/` and `repositories/` should import
`AsyncSession` usage patterns from here directly — services receive a
session via dependency injection (`DbSessionDep`, wired into the FastAPI
app in Step 4), they never construct one.

No module-level engine is created at import time — `get_engine()` /
`get_sessionmaker()` build lazily from an injected `DatabaseConfig`, so
tests can point at a different (e.g. in-memory) database without needing
to reload this module or monkeypatch a global.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import DatabaseConfig, Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _ensure_sqlite_parent_dir_exists(database_url: str) -> None:
    """SQLite (unlike Postgres/MySQL) needs its target file's parent
    directory to already exist — it raises `unable to open database
    file` otherwise, rather than creating one. `.env.example`'s default
    (`sqlite+aiosqlite:///./data/netmon.db`) points at a `data/`
    directory that doesn't exist until something creates it, so we do
    that here, once, before the engine ever opens a connection. No-op
    for non-SQLite URLs and for `:memory:` databases (nothing to create).

    URL shape reminder (verified against urllib.parse.urlparse):
      sqlite+aiosqlite:///./data/netmon.db   -> path='/./data/netmon.db' (relative)
      sqlite+aiosqlite:////tmp/abs/netmon.db -> path='//tmp/abs/netmon.db' (absolute)
      sqlite+aiosqlite:///:memory:           -> path='/:memory:'
    In every case, stripping exactly one leading '/' from `.path`
    recovers the actual filesystem path SQLAlchemy will open.
    """
    if not database_url.startswith("sqlite"):
        return

    path_part = urlparse(database_url).path
    if not path_part.startswith("/"):
        return
    db_path_str = path_part[1:]

    if db_path_str in ("", ":memory:"):
        return

    Path(db_path_str).parent.mkdir(parents=True, exist_ok=True)


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection: object, connection_record: object) -> None:
    """SQLite has foreign key enforcement OFF by default, per-connection.
    Without this, Incident -> TracerouteResult/TcpCapture/Alert foreign
    keys are accepted silently but never enforced. Fires for every new
    DBAPI connection; the PRAGMA is simply ignored by non-SQLite
    backends reached through this hook in a mixed test suite, so no
    dialect guard is required."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    except Exception:  # noqa: BLE001 — non-SQLite DBAPI connections reject the PRAGMA; ignore
        pass
    finally:
        cursor.close()


@lru_cache(maxsize=8)
def _build_engine(database_url: str, echo: bool) -> AsyncEngine:
    """Cached on (url, echo), not call-count — so tests that build a
    second engine against a different URL (e.g. a tmp-file SQLite db)
    get a distinct engine rather than the production one, while repeat
    calls with the same URL reuse the same connection pool."""
    _ensure_sqlite_parent_dir_exists(database_url)
    return create_async_engine(database_url, echo=echo, future=True)


def get_engine(config: DatabaseConfig, *, echo: bool = False) -> AsyncEngine:
    """Returns the process-wide engine for `config.url`. Safe to call
    repeatedly — subsequent calls with the same URL return the same
    engine instance."""
    return _build_engine(config.url, echo)


def get_sessionmaker(
    config: DatabaseConfig, *, echo: bool = False
) -> async_sessionmaker[AsyncSession]:
    engine = get_engine(config, echo=echo)
    return async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


async def get_db_session(settings: Settings | None = None) -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields a session, commits on clean exit, rolls
    back and re-raises on exception.

    `settings` defaults to `get_settings()` when not explicitly passed —
    this function deliberately does NOT import `fastapi` or use
    `Depends` itself, consistent with `core/config.py` and
    `core/logging.py` staying framework-agnostic. Step 4's `core/deps.py`
    wraps this in a thin `Depends`-based adapter (`DbSessionDep`) for
    actual use in `api/` routers.
    """
    resolved_settings = settings or get_settings()
    session_factory = get_sessionmaker(
        resolved_settings.database, echo=resolved_settings.app_debug
    )
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_models(config: DatabaseConfig, *, echo: bool = False) -> None:
    """Create all tables from `Base.metadata` if they don't exist.

    This is a development/test convenience (used by integration tests
    and local dev bootstrapping), NOT the production schema-management
    path — production schema changes go through Alembic migrations
    (`alembic/`), never `create_all`, so schema history stays auditable
    and reversible.
    """
    from app import models  # noqa: F401  (import registers all models on Base.metadata)
    from app.database.base import Base

    engine = get_engine(config, echo=echo)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database.models_initialized", extra={"url": config.url})


async def dispose_engine(config: DatabaseConfig) -> None:
    """Cleanly closes the connection pool. Called from the FastAPI
    lifespan shutdown hook in Step 4."""
    engine = get_engine(config)
    await engine.dispose()
    _build_engine.cache_clear()

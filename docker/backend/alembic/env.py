"""Alembic migration environment.

Contract: this file is the only place migrations and the live app agree
on two things — (1) the database URL, sourced from
`app.core.config.get_settings()` rather than duplicated in `alembic.ini`,
and (2) the target schema, sourced from `Base.metadata` via `from app
import models` — so `alembic revision --autogenerate` diffs against the
actual current model definitions, not a hand-maintained copy.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app import models  # noqa: F401  (registers all models on Base.metadata)
from app.core.config import get_settings
from app.database.base import Base
from app.database.session import _ensure_sqlite_parent_dir_exists

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_database_url() -> str:
    return get_settings().database.url


def run_migrations_offline() -> None:
    """Generate SQL scripts without a live DB connection
    (`alembic upgrade --sql`)."""
    context.configure(
        url=_get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection) -> None:  # type: ignore[no-untyped-def]
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations against a live DB using the project's async engine
    machinery, consistent with how the app itself connects."""
    database_url = _get_database_url()
    _ensure_sqlite_parent_dir_exists(database_url)
    connectable: AsyncEngine = create_async_engine(database_url, future=True)

    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())

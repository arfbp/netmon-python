"""SQLAlchemy declarative base.

Contract: every model in `app/models/` inherits from `Base` defined here,
and nowhere else. A single shared `Base.metadata` is what lets Alembic's
`env.py` (and `--autogenerate`) see every table in one place.

The naming convention is not cosmetic: SQLite/Postgres will happily let
SQLAlchemy generate unnamed constraints, which makes Alembic's
autogenerate diffs unstable (a constraint gets dropped and recreated
under a new random name on every migration). Fixing the naming
convention here, before any model exists, avoids ever having to fix it
retroactively across a growing migration history.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base for all ORM models. Holds no columns of its own —
    see `database/mixins.py` for reusable column groups."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

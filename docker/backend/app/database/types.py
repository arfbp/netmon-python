"""Shared SQLAlchemy column-type helpers.

Contract: this module holds column *type* construction only — no ORM
mapping, no business logic. Every enum-backed column in `models/` goes
through `enum_column()` so the storage strategy (VARCHAR, not native SQL
enum) is decided in exactly one place.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TypeVar

from sqlalchemy import Enum as SAEnum

E = TypeVar("E", bound=StrEnum)


def enum_column(enum_cls: type[E], *, length: int = 32) -> SAEnum:
    """Build a `sa.Enum` column type for a `StrEnum`, stored as
    `VARCHAR(length)` rather than a native Postgres/MySQL enum type
    (`native_enum=False`).

    Why non-native: the brief requires an easy SQLite -> PostgreSQL
    migration path. Native Postgres enums need `ALTER TYPE ... ADD
    VALUE` (which can't run inside a transaction on older Postgres) any
    time a member is added to a Python enum — a VARCHAR + CHECK
    constraint is a plain Alembic column-level migration instead, on
    both backends identically.
    """
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=length,
        values_callable=lambda cls: [member.value for member in cls],
    )

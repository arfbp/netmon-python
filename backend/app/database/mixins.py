"""Reusable column mixins for ORM models.

Contract: a mixin here holds column definitions only — no relationships,
no business logic. Keeping `id`/`created_at` definitions in one place
means every model gets identical column types/defaults without copy-
pasting them nine times (one per table), and a future change (e.g.
switching PK strategy) touches one file.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column


class IntPKMixin:
    """Auto-incrementing integer primary key.

    Chosen over UUID for the high-frequency history tables (PingHistory
    writes every 2 seconds) — integer PKs are smaller, faster to index,
    and sequential inserts avoid the B-tree fragmentation UUIDv4 PKs
    cause at this write volume. Nothing in these tables is referenced
    across service boundaries by ID, so UUID's "globally unique without
    coordination" benefit isn't needed here.
    """

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)


class CreatedAtMixin:
    """Record-creation timestamp, distinct from any domain 'timestamp'
    column a model may also have (e.g. PingHistory.timestamp is *when
    the ping happened*; created_at would be *when the row was written*
    — for history tables these are effectively the same instant, so
    only models where the distinction matters — Incident, Alert,
    TcpCapture, Setting — use this mixin)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

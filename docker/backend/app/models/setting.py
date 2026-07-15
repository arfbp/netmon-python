"""Setting: runtime-configurable key/value store, editable from the
dashboard (Step 7+) without a restart.

Not to be confused with `app.core.config.Settings` (Step 2) — that's
process-startup configuration from environment variables (targets,
intervals, thresholds as defaults). This table is for values an operator
changes *while the app is running* (e.g. temporarily muting alerts,
adjusting a threshold on the fly). Services that need a "live" value
check this table first and fall back to `core.config.Settings` if no
override row exists — that resolution order is implemented in
`services/settings_service.py` in a later step, not here; this model is
storage only.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import IntPKMixin


class Setting(Base, IntPKMixin):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    # JSON, not a plain string column: values vary in shape (a threshold
    # is a number, ping_targets is a list, alerts_enabled is a bool) —
    # one typed JSON column avoids either a wide sparse
    # value_int/value_str/value_bool table or per-setting-type subtables
    # for what is fundamentally a small, low-write-volume config table.
    value: Mapped[dict | list | str | float | bool] = mapped_column(JSON, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Setting key={self.key!r} value={self.value!r}>"

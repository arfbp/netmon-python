"""PingHistory: one row per ping probe against one target.

The Ping Monitor (Step 6) pings every configured target (gateway, ISP
gateway, 1.1.1.1, 8.8.8.8) every `settings.ping.interval_seconds` and
writes one row per target per tick — not one row per tick averaged
across targets — so a LAN-vs-WAN problem is distinguishable after the
fact (e.g. gateway healthy but 1.1.1.1 timing out points at the ISP,
not the LAN).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import Severity
from app.database.base import Base
from app.database.mixins import IntPKMixin
from app.database.types import enum_column


class PingHistory(Base, IntPKMixin):
    __tablename__ = "ping_history"
    __table_args__ = (
        # Every dashboard query is "give me target X's pings since time
        # Y" — this composite index is what makes that a range scan
        # instead of a full-table scan once history grows to millions
        # of rows (2s interval x 4 targets = ~172k rows/day).
        Index("ix_ping_history_target_timestamp", "target", "timestamp"),
    )

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    target: Mapped[str] = mapped_column(String(255), nullable=False)

    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_timeout: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Rolling statistics computed by the monitor at write time (per the
    # brief: "Do NOT simply store ping. Store analytics.") — computed
    # once here rather than recomputed on every dashboard read, since
    # the underlying window (e.g. last N probes for this target) is
    # cheap to maintain incrementally in the monitor but expensive to
    # recompute per-query at scale.
    jitter_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    rolling_avg_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    packet_loss_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    severity: Mapped[Severity] = mapped_column(
        enum_column(Severity), nullable=False, default=Severity.EXCELLENT
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return (
            f"<PingHistory id={self.id} target={self.target!r} "
            f"latency_ms={self.latency_ms} severity={self.severity}>"
        )

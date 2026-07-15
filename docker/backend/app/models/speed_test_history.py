"""SpeedTestHistory: one row per hourly speed test run.

Low write volume (per `settings.speedtest.interval_seconds`, default
hourly) compared to PingHistory, so no composite index is needed beyond
the primary key + a plain timestamp index for the historical charts
(Step 15).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import IntPKMixin


class SpeedTestHistory(Base, IntPKMixin):
    __tablename__ = "speed_test_history"
    __table_args__ = (Index("ix_speed_test_history_timestamp", "timestamp"),)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    download_mbps: Mapped[float | None] = mapped_column(Float, nullable=True)
    upload_mbps: Mapped[float | None] = mapped_column(Float, nullable=True)
    ping_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    server_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    server_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    is_error: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<SpeedTestHistory id={self.id} download_mbps={self.download_mbps} "
            f"upload_mbps={self.upload_mbps}>"
        )

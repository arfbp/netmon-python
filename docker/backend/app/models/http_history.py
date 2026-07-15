"""HTTPHistory: one row per HTTP GET probe, with full timing breakdown.

The HTTP Monitor (Step 9) hits `settings.http.test_url` on its own
interval. Storing the DNS/TCP/TLS/TTFB breakdown (not just total time)
is what lets the incident engine later distinguish "DNS is slow" from
"the remote server is slow" from "TLS handshake is slow" without
re-running diagnostics after the fact.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import IntPKMixin


class HTTPHistory(Base, IntPKMixin):
    __tablename__ = "http_history"
    __table_args__ = (Index("ix_http_history_url_timestamp", "url", "timestamp"),)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)

    dns_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    tcp_connect_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    tls_handshake_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    ttfb_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_error: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<HTTPHistory id={self.id} url={self.url!r} "
            f"status_code={self.status_code} total_time_ms={self.total_time_ms}>"
        )

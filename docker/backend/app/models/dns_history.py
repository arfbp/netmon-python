"""DNSHistory: one row per (domain, resolver) DNS resolution probe.

The DNS Monitor (Step 8) tests every configured domain against every
configured resolver on its own interval — recording per-resolver, not
just an aggregate, so a single misbehaving resolver is identifiable
without cross-referencing logs.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import IntPKMixin


class DNSHistory(Base, IntPKMixin):
    __tablename__ = "dns_history"
    __table_args__ = (Index("ix_dns_history_domain_timestamp", "domain", "timestamp"),)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    resolver: Mapped[str] = mapped_column(String(64), nullable=False)

    response_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_timeout: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_error: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<DNSHistory id={self.id} domain={self.domain!r} "
            f"resolver={self.resolver!r} response_time_ms={self.response_time_ms}>"
        )

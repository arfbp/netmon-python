"""TcpCapture: metadata for an on-incident tcpdump packet capture.

The actual .pcap file lives on disk under `settings.tcpdump.storage_dir`
— this table stores the pointer + lifecycle metadata, not the packet
bytes themselves (a 5MB-value-per-key style constraint doesn't apply
here since this isn't going through the storage API, but a multi-hundred
-MB PCAP has no business living in a SQL row regardless of backend).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import IntPKMixin
from app.database.types import enum_column


class CaptureStatus(StrEnum):
    """Lifecycle of a single capture. Not in core/enums.py because
    nothing outside this model and the (future) TCPDump monitor needs
    it — core/enums.py is reserved for vocabulary shared across
    multiple layers/models."""

    RECORDING = "recording"
    COMPLETED = "completed"
    FAILED = "failed"


class TcpCapture(Base, IntPKMixin):
    __tablename__ = "tcp_captures"

    incident_id: Mapped[int | None] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), nullable=True
    )

    interface: Mapped[str] = mapped_column(String(64), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)

    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[CaptureStatus] = mapped_column(
        enum_column(CaptureStatus), nullable=False, default=CaptureStatus.RECORDING
    )

    incident: Mapped["Incident | None"] = relationship(back_populates="tcp_captures")  # noqa: F821

    @property
    def duration_seconds(self) -> float | None:
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time).total_seconds()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TcpCapture id={self.id} interface={self.interface!r} status={self.status}>"

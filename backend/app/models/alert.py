"""Alert: a delivery record produced by the Alert Engine (Step 11).

Architecture-only for most channels per the brief — this table's shape
is deliberately channel-agnostic (`channel` + `message` + delivery
status) so adding Telegram/Discord/Email later is new code in
`services/alerting/`, not a schema change here.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import AlertChannel
from app.database.base import Base
from app.database.mixins import CreatedAtMixin, IntPKMixin
from app.database.types import enum_column


class AlertStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class Alert(Base, IntPKMixin, CreatedAtMixin):
    __tablename__ = "alerts"

    incident_id: Mapped[int | None] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), nullable=True
    )

    channel: Mapped[AlertChannel] = mapped_column(enum_column(AlertChannel), nullable=False)
    message: Mapped[str] = mapped_column(String(2000), nullable=False)

    status: Mapped[AlertStatus] = mapped_column(
        enum_column(AlertStatus), nullable=False, default=AlertStatus.PENDING
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    incident: Mapped["Incident | None"] = relationship(back_populates="alerts")  # noqa: F821

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Alert id={self.id} channel={self.channel} status={self.status}>"

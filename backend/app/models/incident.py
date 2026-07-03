"""Incident: the aggregate root of the incident lifecycle
(Started -> Active -> Recovered), per the brief.

Created and transitioned exclusively by the Incident Engine (Step 10) —
no other layer writes to this table. TracerouteResult, TcpCapture, and
Alert rows optionally reference an Incident via foreign key, since
diagnostics/alerts are triggered *by* an incident, not the other way
around.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import IncidentStatus, IncidentType, MonitorType, Severity
from app.database.base import Base
from app.database.mixins import CreatedAtMixin, IntPKMixin
from app.database.types import enum_column


class Incident(Base, IntPKMixin, CreatedAtMixin):
    __tablename__ = "incidents"

    incident_type: Mapped[IncidentType] = mapped_column(enum_column(IncidentType), nullable=False)
    status: Mapped[IncidentStatus] = mapped_column(
        enum_column(IncidentStatus), nullable=False, default=IncidentStatus.STARTED
    )
    severity: Mapped[Severity] = mapped_column(enum_column(Severity), nullable=False)

    # Which monitor's data triggered this incident — lets the dashboard
    # timeline (Step 7/15) show a source icon without joining across
    # every history table to guess.
    triggering_monitor: Mapped[MonitorType] = mapped_column(
        enum_column(MonitorType), nullable=False
    )

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recovered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    summary: Mapped[str] = mapped_column(String(1000), nullable=False)

    # Free-form structured context (e.g. {"target": "1.1.1.1",
    # "latency_ms": 420, "threshold_ms": 300}) — the specific trigger
    # detail varies per incident_type, so a fixed column set would force
    # either a wide sparse table or a type-specific subtable per
    # IncidentType. JSON keeps the core columns (used in every query:
    # filter/sort by type/status/severity/time) properly typed and
    # indexable, while trigger-specific detail stays flexible.
    context: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    traceroute_results: Mapped[list["TracerouteResult"]] = relationship(  # noqa: F821
        back_populates="incident", cascade="all, delete-orphan"
    )
    tcp_captures: Mapped[list["TcpCapture"]] = relationship(  # noqa: F821
        back_populates="incident", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["Alert"]] = relationship(  # noqa: F821
        back_populates="incident", cascade="all, delete-orphan"
    )

    @property
    def duration_seconds(self) -> float | None:
        """Computed, not stored — storing it would require updating this
        row on every tick while ACTIVE just to keep a redundant column
        fresh. None while the incident hasn't recovered yet."""
        if self.recovered_at is None:
            return None
        return (self.recovered_at - self.started_at).total_seconds()

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Incident id={self.id} type={self.incident_type} "
            f"status={self.status} severity={self.severity}>"
        )

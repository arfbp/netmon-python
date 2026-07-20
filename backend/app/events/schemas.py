"""Base event contract.

Contract: concrete events (`PingResultEvent`, `PacketLossDetectedEvent`,
...) subclass `DomainEvent`, starting Step 6 when the first monitor
exists to produce them. Frozen dataclass, not a Pydantic model — events
are internal, in-process messages between application layers, not data
crossing a serialization boundary (that happens once, in
`websocket/event_forwarder.py`, when an event is turned into an outbound
`WSMessage`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.core.enums import IncidentStatus, IncidentType, Severity


@dataclass(frozen=True, slots=True)
class DomainEvent:
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class PingResultEvent(DomainEvent):
    """Published once per target, per Ping Monitor tick (Step 6).
    Consumed by the WebSocket forwarder (real-time dashboard update) and,
    from Step 10 onward, the Incident Engine (packet-loss/latency
    incident detection) — neither consumer is known to the Ping Monitor
    itself.
    """

    target: str = ""
    latency_ms: float | None = None
    is_timeout: bool = False
    jitter_ms: float | None = None
    rolling_avg_ms: float | None = None
    packet_loss_pct: float = 0.0
    severity: Severity = Severity.EXCELLENT


@dataclass(frozen=True, slots=True)
class IncidentEvent(DomainEvent):
    incident_id: int = 0
    incident_type: IncidentType = IncidentType.INTERNET_DOWN
    status: IncidentStatus = IncidentStatus.STARTED
    severity: Severity = Severity.EXCELLENT
    target: str = ""
    summary: str = ""
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    recovered_at: datetime | None = None

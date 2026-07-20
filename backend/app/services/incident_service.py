"""Reactive incident engine.

The service subscribes to PingResultEvent and opens, updates, and
recovers Incident rows based on consecutive bad/healthy ticks. It is
intentionally not a scheduler task — it reacts to the event bus, which
matches the architecture rationale established in Step 1.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.enums import IncidentStatus, IncidentType, MonitorType, Severity
from app.events.bus import EventBus
from app.events.schemas import IncidentEvent, PingResultEvent
from app.models import Incident
from app.monitors.network_utils import detect_default_gateway
from app.repositories.incident_repository import IncidentRepository
from app.services.incident_classifier import classify_incident_type

PingResultHandler = Callable[[PingResultEvent], Awaitable[None]]


@dataclass(slots=True)
class _TargetState:
    consecutive_bad_ticks: int = 0
    consecutive_good_ticks: int = 0
    active_incident_id: int | None = None
    active_incident_type: IncidentType | None = None
    active_severity: Severity | None = None


class IncidentService:
    def __init__(
        self,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
        event_bus: EventBus,
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory
        self._event_bus = event_bus
        self._lock = asyncio.Lock()
        self._state_by_target: dict[str, _TargetState] = {}
        self._latest_results: dict[str, PingResultEvent] = {}
        self._gateway_targets = self._resolve_gateway_targets()
        self._internet_targets = [
            target for target in self._settings.ping.targets if target not in self._gateway_targets
        ]
        self._event_bus.subscribe(PingResultEvent, self._handle_ping_result)

    async def bootstrap(self) -> None:
        """Loads any already-active incidents into memory.

        This lets a restarted process continue an ongoing incident
        without creating a duplicate row on the first new bad ping.
        """
        async with self._session_factory() as session:
            repo = IncidentRepository(session)
            active_incidents = await repo.get_active()

        for incident in active_incidents:
            target = self._incident_target(incident)
            if target is None:
                continue
            state = self._state_by_target.setdefault(target, _TargetState())
            if state.active_incident_id is None:
                state.active_incident_id = incident.id
                state.active_incident_type = incident.incident_type
                state.active_severity = incident.severity

    def _resolve_gateway_targets(self) -> set[str]:
        targets: set[str] = set()
        if self._settings.ping.isp_gateway:
            targets.add(self._settings.ping.isp_gateway)
        if self._settings.ping.gateway_auto_detect:
            detected_gateway = detect_default_gateway()
            if detected_gateway:
                targets.add(detected_gateway)
        return targets

    @staticmethod
    def _incident_target(incident: Incident) -> str | None:
        context = incident.context or {}
        target = context.get("target")
        return str(target) if target is not None else None

    def _build_summary(self, incident_type: IncidentType, event: PingResultEvent, is_gateway_target: bool) -> str:
        if incident_type == IncidentType.GATEWAY_DOWN:
            return f"Gateway target {event.target} is offline"
        if incident_type == IncidentType.INTERNET_DOWN:
            return f"All internet targets are offline (triggered by {event.target})"
        if incident_type == IncidentType.PACKET_LOSS:
            return f"Packet loss on {event.target} reached {event.packet_loss_pct:.0f}%"
        if incident_type == IncidentType.INTERNET_SLOW:
            latency = "unknown" if event.latency_ms is None else f"{event.latency_ms:.1f} ms"
            return f"Latency on {event.target} is {event.severity.value} ({latency})"
        if is_gateway_target:
            return f"Gateway target {event.target} is unhealthy"
        return f"Internet target {event.target} is unhealthy"

    def _build_context(
        self,
        event: PingResultEvent,
        *,
        is_gateway_target: bool,
        all_internet_targets_offline: bool,
    ) -> dict[str, object]:
        return {
            "target": event.target,
            "triggering_monitor": MonitorType.PING.value,
            "latency_ms": event.latency_ms,
            "packet_loss_pct": event.packet_loss_pct,
            "severity": event.severity.value,
            "is_gateway_target": is_gateway_target,
            "all_internet_targets_offline": all_internet_targets_offline,
        }

    def _build_incident_event(self, incident: Incident, target: str) -> IncidentEvent:
        return IncidentEvent(
            incident_id=incident.id,
            incident_type=incident.incident_type,
            status=incident.status,
            severity=incident.severity,
            target=target,
            summary=incident.summary,
            started_at=incident.started_at,
            recovered_at=incident.recovered_at,
        )

    def _all_internet_targets_offline(self) -> bool:
        if not self._internet_targets:
            return False
        for target in self._internet_targets:
            result = self._latest_results.get(target)
            if result is None or result.severity != Severity.OFFLINE:
                return False
        return True

    async def _handle_ping_result(self, event: PingResultEvent) -> None:
        async with self._lock:
            self._latest_results[event.target] = event
            is_gateway_target = event.target in self._gateway_targets
            all_internet_targets_offline = self._all_internet_targets_offline()
            incident_type = classify_incident_type(
                event.target,
                event.severity,
                event.packet_loss_pct,
                is_gateway_target,
                all_internet_targets_offline,
                self._settings.thresholds,
            )
            state = self._state_by_target.setdefault(event.target, _TargetState())

            if state.active_incident_id is None:
                if incident_type is None:
                    state.consecutive_bad_ticks = 0
                    state.consecutive_good_ticks = min(
                        state.consecutive_good_ticks + 1,
                        self._settings.incident.consecutive_ticks_to_recover,
                    )
                    return

                state.consecutive_bad_ticks += 1
                state.consecutive_good_ticks = 0
                if state.consecutive_bad_ticks < self._settings.incident.consecutive_ticks_to_open:
                    return

                await self._open_incident(event, state, incident_type, is_gateway_target, all_internet_targets_offline)
                return

            if incident_type is None:
                state.consecutive_good_ticks += 1
                state.consecutive_bad_ticks = 0
                if state.consecutive_good_ticks < self._settings.incident.consecutive_ticks_to_recover:
                    return

                await self._recover_incident(event, state)
                return

            state.consecutive_bad_ticks += 1
            state.consecutive_good_ticks = 0
            await self._update_active_incident_if_needed(
                event,
                state,
                incident_type,
                is_gateway_target=is_gateway_target,
                all_internet_targets_offline=all_internet_targets_offline,
            )

    async def _open_incident(
        self,
        event: PingResultEvent,
        state: _TargetState,
        incident_type: IncidentType,
        is_gateway_target: bool,
        all_internet_targets_offline: bool,
    ) -> None:
        async with self._session_factory() as session:
            repo = IncidentRepository(session)
            incident = Incident(
                incident_type=incident_type,
                status=IncidentStatus.ACTIVE,
                severity=event.severity,
                triggering_monitor=MonitorType.PING,
                started_at=event.occurred_at,
                recovered_at=None,
                summary=self._build_summary(incident_type, event, is_gateway_target),
                context=self._build_context(
                    event,
                    is_gateway_target=is_gateway_target,
                    all_internet_targets_offline=all_internet_targets_offline,
                ),
            )
            await repo.add(incident)
            await session.commit()

        state.active_incident_id = incident.id
        state.active_incident_type = incident.incident_type
        state.active_severity = incident.severity
        state.consecutive_bad_ticks = 0

        await self._event_bus.publish(self._build_incident_event(incident, event.target))

    async def _update_active_incident_if_needed(
        self,
        event: PingResultEvent,
        state: _TargetState,
        incident_type: IncidentType,
        *,
        is_gateway_target: bool,
        all_internet_targets_offline: bool,
    ) -> None:
        if state.active_incident_id is None:
            return

        async with self._session_factory() as session:
            repo = IncidentRepository(session)
            incident = await repo.get_by_id(state.active_incident_id)
            if incident is None:
                state.active_incident_id = None
                state.active_incident_type = None
                state.active_severity = None
                return

            changed = False
            if incident.incident_type != incident_type:
                incident.incident_type = incident_type
                changed = True

            if Severity.rank(event.severity) > Severity.rank(incident.severity):
                incident.severity = event.severity
                changed = True

            if changed:
                incident.summary = self._build_summary(incident_type, event, is_gateway_target)
                incident.context = self._build_context(
                    event,
                    is_gateway_target=is_gateway_target,
                    all_internet_targets_offline=all_internet_targets_offline,
                )
                await session.commit()

        state.active_incident_type = incident_type
        if Severity.rank(event.severity) > Severity.rank(state.active_severity or Severity.EXCELLENT):
            state.active_severity = event.severity

        if changed:
            await self._event_bus.publish(self._build_incident_event(incident, event.target))

    async def _recover_incident(self, event: PingResultEvent, state: _TargetState) -> None:
        if state.active_incident_id is None:
            return

        async with self._session_factory() as session:
            repo = IncidentRepository(session)
            incident = await repo.get_by_id(state.active_incident_id)
            if incident is None:
                state.active_incident_id = None
                state.active_incident_type = None
                state.active_severity = None
                return

            incident.status = IncidentStatus.RECOVERED
            incident.recovered_at = event.occurred_at
            await session.commit()

        state.active_incident_id = None
        state.active_incident_type = None
        state.active_severity = None
        state.consecutive_bad_ticks = 0
        state.consecutive_good_ticks = 0

        await self._event_bus.publish(self._build_incident_event(incident, event.target))
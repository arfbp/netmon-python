"""Integration tests for the reactive IncidentService."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.enums import IncidentStatus, IncidentType, Severity
from app.database.base import Base
from app.events.bus import EventBus
from app.events.schemas import IncidentEvent, PingResultEvent
from app.models import Incident
from app.services.incident_service import IncidentService


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "database_url": "sqlite+aiosqlite:///:memory:",
        "app_env": "development",
        "monitors_enabled": False,
        "ping_targets": ["1.1.1.1"],
        "ping_gateway_auto_detect": False,
        "ping_isp_gateway": None,
        "incident_consecutive_ticks_to_open": 2,
        "incident_consecutive_ticks_to_recover": 2,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)  # type: ignore[arg-type]


@pytest_asyncio.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


def _ping_event(
    *,
    target: str,
    occurred_at: datetime,
    severity: Severity,
    packet_loss_pct: float = 0.0,
    latency_ms: float | None = 12.3,
) -> PingResultEvent:
    return PingResultEvent(
        occurred_at=occurred_at,
        target=target,
        latency_ms=latency_ms,
        is_timeout=severity == Severity.OFFLINE,
        jitter_ms=None,
        rolling_avg_ms=latency_ms,
        packet_loss_pct=packet_loss_pct,
        severity=severity,
    )


def _normalize_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


class TestIncidentLifecycle:
    async def test_open_update_and_recover_incident(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        settings = _settings()
        bus = EventBus()
        service = IncidentService(settings, session_factory, bus)
        await service.bootstrap()

        incident_events: list[IncidentEvent] = []

        async def capture(event: IncidentEvent) -> None:
            incident_events.append(event)

        bus.subscribe(IncidentEvent, capture)

        started = datetime(2026, 1, 1, tzinfo=UTC)
        await bus.publish(
            _ping_event(target="1.1.1.1", occurred_at=started, severity=Severity.WARNING)
        )
        await bus.publish(
            _ping_event(
                target="1.1.1.1",
                occurred_at=started + timedelta(seconds=2),
                severity=Severity.WARNING,
            )
        )
        await bus.publish(
            _ping_event(
                target="1.1.1.1",
                occurred_at=started + timedelta(seconds=4),
                severity=Severity.CRITICAL,
            )
        )
        await bus.publish(
            _ping_event(
                target="1.1.1.1",
                occurred_at=started + timedelta(seconds=6),
                severity=Severity.EXCELLENT,
            )
        )
        await bus.publish(
            _ping_event(
                target="1.1.1.1",
                occurred_at=started + timedelta(seconds=8),
                severity=Severity.EXCELLENT,
            )
        )

        async with session_factory() as session:
            incident = (await session.execute(select(Incident))).scalar_one()

        assert incident.incident_type == IncidentType.INTERNET_SLOW
        assert incident.status == IncidentStatus.RECOVERED
        assert incident.severity == Severity.CRITICAL
        assert _normalize_utc(incident.started_at) == started + timedelta(seconds=2)
        assert _normalize_utc(incident.recovered_at) == started + timedelta(seconds=8)
        assert incident.context is not None
        assert incident.context["target"] == "1.1.1.1"

        assert [event.status for event in incident_events] == [
            IncidentStatus.ACTIVE,
            IncidentStatus.ACTIVE,
            IncidentStatus.RECOVERED,
        ]
        assert {event.incident_id for event in incident_events} == {incident.id}

"""Integration tests for PingMonitor.

Uses a fake, injectable pinger (no real network calls — deterministic
and fast) against a real in-memory SQLite engine and a real EventBus,
proving the actual wiring: tick() -> DB row -> published event, and that
rolling-window analytics accumulate correctly across multiple ticks.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.core.enums import Severity
from app.database.base import Base
from app.events.bus import EventBus
from app.events.schemas import PingResultEvent
from app.models import PingHistory
from app.monitors.ping_monitor import PingMonitor


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "ping_targets": ["1.1.1.1", "8.8.8.8"],
        "ping_gateway_auto_detect": False,
        "ping_isp_gateway": None,
        "ping_rolling_window_size": 5,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)  # type: ignore[arg-type]


@pytest_asyncio.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


def _scripted_pinger(responses: dict[str, list[float | None]]):
    """Returns a fake pinger that yields the next value from
    `responses[target]` on each call, so a test can script exactly what
    each tick "measures" per target without touching the network."""
    indices: dict[str, int] = dict.fromkeys(responses, 0)

    async def pinger(address: str, timeout_seconds: float, privileged: bool) -> float | None:
        i = indices[address]
        indices[address] = i + 1
        return responses[address][i]

    return pinger


class TestSingleTick:
    async def test_tick_writes_one_row_per_target(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        settings = _settings(ping_targets=["1.1.1.1", "8.8.8.8"])
        bus = EventBus()
        pinger = _scripted_pinger({"1.1.1.1": [10.0], "8.8.8.8": [12.0]})
        monitor = PingMonitor(settings, session_factory, bus, pinger=pinger)

        await monitor.tick()

        async with session_factory() as session:
            rows = (await session.execute(select(PingHistory))).scalars().all()
        assert len(rows) == 2
        targets = {row.target for row in rows}
        assert targets == {"1.1.1.1", "8.8.8.8"}

    async def test_successful_probe_row_shape(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        settings = _settings(ping_targets=["1.1.1.1"])
        bus = EventBus()
        pinger = _scripted_pinger({"1.1.1.1": [15.0]})
        monitor = PingMonitor(settings, session_factory, bus, pinger=pinger)

        await monitor.tick()

        async with session_factory() as session:
            row = (await session.execute(select(PingHistory))).scalar_one()
        assert row.latency_ms == 15.0
        assert row.is_timeout is False
        assert row.packet_loss_pct == 0.0
        assert row.severity in (Severity.EXCELLENT, Severity.GOOD)

    async def test_timeout_probe_row_shape(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        settings = _settings(ping_targets=["1.1.1.1"])
        bus = EventBus()
        pinger = _scripted_pinger({"1.1.1.1": [None]})
        monitor = PingMonitor(settings, session_factory, bus, pinger=pinger)

        await monitor.tick()

        async with session_factory() as session:
            row = (await session.execute(select(PingHistory))).scalar_one()
        assert row.latency_ms is None
        assert row.is_timeout is True
        assert row.packet_loss_pct == 100.0  # only sample so far, and it timed out
        assert row.severity == Severity.OFFLINE

    async def test_tick_publishes_one_event_per_target(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        settings = _settings(ping_targets=["1.1.1.1", "8.8.8.8"])
        bus = EventBus()
        received: list[PingResultEvent] = []

        async def handler(event: PingResultEvent) -> None:
            received.append(event)

        bus.subscribe(PingResultEvent, handler)

        pinger = _scripted_pinger({"1.1.1.1": [10.0], "8.8.8.8": [12.0]})
        monitor = PingMonitor(settings, session_factory, bus, pinger=pinger)

        await monitor.tick()

        assert len(received) == 2
        assert {e.target for e in received} == {"1.1.1.1", "8.8.8.8"}


class TestRollingWindowAcrossTicks:
    async def test_packet_loss_pct_reflects_window_history(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        settings = _settings(ping_targets=["1.1.1.1"], ping_rolling_window_size=4)
        bus = EventBus()
        # 2 successes, then 2 timeouts -> 50% loss over the 4-sample window
        pinger = _scripted_pinger({"1.1.1.1": [10.0, 12.0, None, None]})
        monitor = PingMonitor(settings, session_factory, bus, pinger=pinger)

        for _ in range(4):
            await monitor.tick()

        async with session_factory() as session:
            rows = (
                (await session.execute(select(PingHistory).order_by(PingHistory.id)))
                .scalars()
                .all()
            )
        assert rows[-1].packet_loss_pct == 50.0

    async def test_jitter_and_rolling_avg_populate_after_multiple_ticks(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        settings = _settings(ping_targets=["1.1.1.1"], ping_rolling_window_size=5)
        bus = EventBus()
        pinger = _scripted_pinger({"1.1.1.1": [10.0, 14.0, 10.0]})
        monitor = PingMonitor(settings, session_factory, bus, pinger=pinger)

        for _ in range(3):
            await monitor.tick()

        async with session_factory() as session:
            rows = (
                (await session.execute(select(PingHistory).order_by(PingHistory.id)))
                .scalars()
                .all()
            )
        last = rows[-1]
        assert last.jitter_ms is not None
        assert last.rolling_avg_ms is not None
        assert last.rolling_avg_ms == pytest.approx((10.0 + 14.0 + 10.0) / 3)


class TestTargetResolution:
    def test_explicit_targets_only_when_gateway_detection_disabled(self) -> None:
        settings = _settings(
            ping_targets=["1.1.1.1", "8.8.8.8"],
            ping_gateway_auto_detect=False,
            ping_isp_gateway=None,
        )
        monitor = PingMonitor(settings, session_factory=None, event_bus=EventBus())  # type: ignore[arg-type]
        assert monitor.targets == ["1.1.1.1", "8.8.8.8"]

    def test_isp_gateway_is_prepended(self) -> None:
        settings = _settings(
            ping_targets=["1.1.1.1"],
            ping_gateway_auto_detect=False,
            ping_isp_gateway="203.0.113.1",
        )
        monitor = PingMonitor(settings, session_factory=None, event_bus=EventBus())  # type: ignore[arg-type]
        assert monitor.targets == ["203.0.113.1", "1.1.1.1"]

    def test_duplicate_targets_are_deduplicated_preserving_order(self) -> None:
        settings = _settings(
            ping_targets=["1.1.1.1", "203.0.113.1"],
            ping_gateway_auto_detect=False,
            ping_isp_gateway="203.0.113.1",
        )
        monitor = PingMonitor(settings, session_factory=None, event_bus=EventBus())  # type: ignore[arg-type]
        assert monitor.targets == ["203.0.113.1", "1.1.1.1"]

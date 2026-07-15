"""Integration tests: real async SQLite engine (in-memory), real ORM
inserts/queries. Confirms models + Base metadata + mixins + enum
columns actually work together, not just that they import cleanly.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import models
from app.core.enums import IncidentStatus, IncidentType, MonitorType, Severity
from app.database.base import Base
from app.models import Alert, AlertStatus, DNSHistory, HTTPHistory, Incident, PingHistory, Setting
from app.models import SpeedTestHistory, TcpCapture, TracerouteResult
from app.models.tcp_capture import CaptureStatus

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """Fresh in-memory SQLite DB per test — no shared state between
    tests, no dependency on a file on disk."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


class TestPingHistory:
    async def test_insert_and_query(self, session: AsyncSession) -> None:
        row = PingHistory(
            timestamp=datetime.now(UTC),
            target="1.1.1.1",
            latency_ms=12.5,
            is_timeout=False,
            jitter_ms=1.2,
            rolling_avg_ms=13.0,
            packet_loss_pct=0.0,
            severity=Severity.EXCELLENT,
        )
        session.add(row)
        await session.commit()

        assert row.id is not None
        assert row.severity == Severity.EXCELLENT

    async def test_timeout_row_allows_null_latency(self, session: AsyncSession) -> None:
        row = PingHistory(
            timestamp=datetime.now(UTC),
            target="8.8.8.8",
            latency_ms=None,
            is_timeout=True,
            packet_loss_pct=100.0,
            severity=Severity.OFFLINE,
        )
        session.add(row)
        await session.commit()
        assert row.latency_ms is None


class TestDNSHistory:
    async def test_insert(self, session: AsyncSession) -> None:
        row = DNSHistory(
            timestamp=datetime.now(UTC),
            domain="cloudflare.com",
            resolver="1.1.1.1",
            response_time_ms=8.4,
        )
        session.add(row)
        await session.commit()
        assert row.id is not None
        assert row.is_error is False


class TestHTTPHistory:
    async def test_insert_full_timing_breakdown(self, session: AsyncSession) -> None:
        row = HTTPHistory(
            timestamp=datetime.now(UTC),
            url="https://www.gstatic.com/generate_204",
            dns_time_ms=2.1,
            tcp_connect_time_ms=5.4,
            tls_handshake_time_ms=10.2,
            ttfb_ms=40.0,
            total_time_ms=45.0,
            status_code=204,
        )
        session.add(row)
        await session.commit()
        assert row.status_code == 204


class TestSpeedTestHistory:
    async def test_insert(self, session: AsyncSession) -> None:
        row = SpeedTestHistory(
            timestamp=datetime.now(UTC), download_mbps=95.4, upload_mbps=20.1, ping_ms=8.0
        )
        session.add(row)
        await session.commit()
        assert row.id is not None


class TestIncidentLifecycleAndRelationships:
    async def test_incident_started_has_no_duration(self, session: AsyncSession) -> None:
        incident = Incident(
            incident_type=IncidentType.PACKET_LOSS,
            status=IncidentStatus.STARTED,
            severity=Severity.HIGH,
            triggering_monitor=MonitorType.PING,
            started_at=datetime.now(UTC),
            summary="Packet loss detected on 1.1.1.1",
            context={"target": "1.1.1.1", "packet_loss_pct": 15.0},
        )
        session.add(incident)
        await session.commit()
        assert incident.duration_seconds is None

    async def test_incident_recovered_has_duration(self, session: AsyncSession) -> None:
        started = datetime.now(UTC)
        recovered = started + timedelta(seconds=42)
        incident = Incident(
            incident_type=IncidentType.INTERNET_DOWN,
            status=IncidentStatus.RECOVERED,
            severity=Severity.CRITICAL,
            triggering_monitor=MonitorType.PING,
            started_at=started,
            recovered_at=recovered,
            summary="Internet down then recovered",
        )
        session.add(incident)
        await session.commit()
        assert incident.duration_seconds is not None
        assert incident.duration_seconds == pytest.approx(42.0)

    async def test_incident_cascades_to_traceroute_and_capture_and_alert(
        self, session: AsyncSession
    ) -> None:
        incident = Incident(
            incident_type=IncidentType.GATEWAY_DOWN,
            status=IncidentStatus.ACTIVE,
            severity=Severity.CRITICAL,
            triggering_monitor=MonitorType.PING,
            started_at=datetime.now(UTC),
            summary="Gateway unreachable",
        )
        session.add(incident)
        await session.flush()

        hop = TracerouteResult(
            run_id="test-run-1",
            incident_id=incident.id,
            target="8.8.8.8",
            timestamp=datetime.now(UTC),
            hop_number=1,
            hop_ip="192.168.1.1",
            latency_ms=1.2,
        )
        capture = TcpCapture(
            incident_id=incident.id,
            interface="eth0",
            file_path="/data/captures/test.pcap",
            start_time=datetime.now(UTC),
            status=CaptureStatus.RECORDING,
        )
        alert = Alert(
            incident_id=incident.id,
            channel="webhook",
            message="Gateway is down",
            status=AlertStatus.PENDING,
        )
        session.add_all([hop, capture, alert])
        await session.commit()

        # Deleting the incident must cascade — no orphaned diagnostic rows.
        await session.delete(incident)
        await session.commit()

        remaining_hops = await session.get(TracerouteResult, hop.id)
        remaining_captures = await session.get(TcpCapture, capture.id)
        remaining_alerts = await session.get(Alert, alert.id)
        assert remaining_hops is None
        assert remaining_captures is None
        assert remaining_alerts is None


class TestSetting:
    async def test_insert_and_unique_key_constraint(self, session: AsyncSession) -> None:
        row = Setting(key="ping_interval_seconds", value=2.0)
        session.add(row)
        await session.commit()
        assert row.updated_at is not None

    async def test_duplicate_key_raises(self, session: AsyncSession) -> None:
        from sqlalchemy.exc import IntegrityError

        session.add(Setting(key="dup", value="a"))
        await session.commit()
        session.add(Setting(key="dup", value="b"))
        with pytest.raises(IntegrityError):
            await session.commit()

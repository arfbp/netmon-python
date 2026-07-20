"""Integration tests for GET /api/v1/incidents/* endpoints."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.enums import IncidentStatus, IncidentType, MonitorType, Severity
from app.database.session import get_sessionmaker
from app.main import create_app
from app.models import Incident


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "database_url": f"sqlite+aiosqlite:///{tmp_path}/test.db",
        "app_env": "development",
        "monitors_enabled": False,
        "ping_targets": ["1.1.1.1"],
        "ping_gateway_auto_detect": False,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)  # type: ignore[arg-type]


class TestIncidentsEndpoints:
    def test_active_and_recent_incidents_are_returned(self, tmp_path: Path) -> None:
        settings = _settings(tmp_path)
        app = create_app(settings)

        with TestClient(app):
            pass

        async def seed() -> None:
            factory = get_sessionmaker(settings.database)
            async with factory() as session:
                session.add(
                    Incident(
                        incident_type=IncidentType.INTERNET_SLOW,
                        status=IncidentStatus.ACTIVE,
                        severity=Severity.WARNING,
                        triggering_monitor=MonitorType.PING,
                        started_at=datetime(2026, 1, 1, tzinfo=UTC),
                        recovered_at=None,
                        summary="Ping latency warning on 1.1.1.1",
                        context={"target": "1.1.1.1"},
                    )
                )
                session.add(
                    Incident(
                        incident_type=IncidentType.PACKET_LOSS,
                        status=IncidentStatus.RECOVERED,
                        severity=Severity.HIGH,
                        triggering_monitor=MonitorType.PING,
                        started_at=datetime(2026, 1, 2, tzinfo=UTC),
                        recovered_at=datetime(2026, 1, 2, 0, 5, tzinfo=UTC),
                        summary="Packet loss on 8.8.8.8",
                        context={"target": "8.8.8.8"},
                    )
                )
                await session.commit()

        asyncio.run(seed())

        with TestClient(app) as client:
            active_response = client.get("/api/v1/incidents/active")
            recent_response = client.get("/api/v1/incidents/recent?limit=50")

        assert active_response.status_code == 200
        active_body = active_response.json()
        assert len(active_body) == 1
        assert active_body[0]["target"] == "1.1.1.1"
        assert active_body[0]["status"] == "active"

        assert recent_response.status_code == 200
        recent_body = recent_response.json()
        assert len(recent_body) == 2
        assert recent_body[0]["target"] == "8.8.8.8"
        assert recent_body[1]["target"] == "1.1.1.1"

"""Integration test for GET /api/v1/ping/latest."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.enums import Severity
from app.database.session import get_sessionmaker
from app.main import create_app
from app.models import PingHistory


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "database_url": f"sqlite+aiosqlite:///{tmp_path}/test.db",
        "app_env": "development",
        "monitors_enabled": False,
        "ping_targets": ["1.1.1.1", "8.8.8.8"],
        "ping_gateway_auto_detect": False,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)  # type: ignore[arg-type]


class TestPingLatestEndpoint:
    def test_returns_empty_list_when_no_data_yet(self, tmp_path: Path) -> None:
        app = create_app(_settings(tmp_path))
        with TestClient(app) as client:
            response = client.get("/api/v1/ping/latest")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_most_recent_row_per_target(self, tmp_path: Path) -> None:
        settings = _settings(tmp_path)
        app = create_app(settings)

        with TestClient(app):
            pass  # runs lifespan once, creating tables, then closes

        async def seed() -> None:
            factory = get_sessionmaker(settings.database)
            async with factory() as session:
                # Two rows for 1.1.1.1 — only the newer one should be returned.
                session.add(
                    PingHistory(
                        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
                        target="1.1.1.1",
                        latency_ms=99.0,
                        is_timeout=False,
                        packet_loss_pct=0.0,
                        severity=Severity.EXCELLENT,
                    )
                )
                session.add(
                    PingHistory(
                        timestamp=datetime(2026, 1, 2, tzinfo=UTC),
                        target="1.1.1.1",
                        latency_ms=12.0,
                        is_timeout=False,
                        jitter_ms=1.0,
                        rolling_avg_ms=12.0,
                        packet_loss_pct=0.0,
                        severity=Severity.GOOD,
                    )
                )
                await session.commit()

        asyncio.run(seed())

        with TestClient(app) as client:
            response = client.get("/api/v1/ping/latest")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1  # only 1.1.1.1 has data; 8.8.8.8 has none
        assert body[0]["target"] == "1.1.1.1"
        assert body[0]["latency_ms"] == 12.0
        assert body[0]["severity"] == "good"

"""Integration tests for the real `/ws` endpoint.

Uses `fastapi.testclient.TestClient` (not httpx's ASGITransport) because
it's the one that supports `.websocket_connect()` and runs the app's
lifespan automatically as a context manager. These tests are
deliberately synchronous (TestClient manages its own event loop via
anyio) — mixing `pytest-asyncio` async tests with TestClient's WebSocket
context manager is unnecessary complexity for what's being verified.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi import Request
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "database_url": f"sqlite+aiosqlite:///{tmp_path}/test.db",
        "app_env": "development",
        # These tests exercise WebSocket connect/heartbeat/event
        # forwarding, not real monitors — keep them isolated from actual
        # background network pinging.
        "monitors_enabled": False,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)  # type: ignore[arg-type]


class TestConnectAndHeartbeat:
    def test_connect_and_receive_heartbeat(self, tmp_path: Path) -> None:
        # Short heartbeat interval so the test doesn't wait long.
        settings = _settings(tmp_path, ws_heartbeat_seconds=1)
        app = create_app(settings)

        with TestClient(app) as client, client.websocket_connect("/ws") as websocket:
            message = websocket.receive_json()
            assert message["type"] == "heartbeat"
            assert "timestamp" in message

    def test_multiple_clients_can_connect_simultaneously(self, tmp_path: Path) -> None:
        settings = _settings(tmp_path, ws_heartbeat_seconds=1)
        app = create_app(settings)

        with TestClient(app) as client:
            with client.websocket_connect("/ws") as ws_a, client.websocket_connect("/ws") as ws_b:
                assert app.state.connection_manager.active_connection_count == 2
                ws_a.receive_json()
                ws_b.receive_json()

    def test_disconnect_removes_connection_from_manager(self, tmp_path: Path) -> None:
        settings = _settings(tmp_path, ws_heartbeat_seconds=5)
        app = create_app(settings)

        with TestClient(app) as client:
            with client.websocket_connect("/ws"):
                assert app.state.connection_manager.active_connection_count == 1
            # Context manager exit closes the connection cleanly.
            assert app.state.connection_manager.active_connection_count == 0


class TestEventForwardingEndToEnd:
    def test_published_domain_event_reaches_connected_client(self, tmp_path: Path) -> None:
        """The real payoff test: an event published on app.state.event_bus
        — exactly how a Step 6+ monitor will do it — must reach a
        connected WebSocket client via the forwarder + connection
        manager, with no direct coupling between the publisher and the
        WebSocket layer."""
        settings = _settings(tmp_path, ws_heartbeat_seconds=30)  # long, so it doesn't interfere
        app = create_app(settings)

        @dataclass(frozen=True, slots=True)
        class DummyPingEvent:
            target: str
            latency_ms: float

        @app.post("/__test_publish")
        async def _publish(request: Request) -> dict[str, bool]:
            await request.app.state.event_bus.publish(
                DummyPingEvent(target="1.1.1.1", latency_ms=12.3)
            )
            return {"ok": True}

        with TestClient(app) as client:
            with client.websocket_connect("/ws") as websocket:
                response = client.post("/__test_publish")
                assert response.status_code == 200

                message = websocket.receive_json()
                assert message["type"] == "dummy_ping"
                assert message["payload"] == {"target": "1.1.1.1", "latency_ms": 12.3}

"""Unit tests for ConnectionManager. Uses `unittest.mock.AsyncMock` in
place of a real `fastapi.WebSocket` — the manager only ever calls
`.accept()` / `.send_json()` on it, so a mock with those methods is a
faithful enough double without needing a real ASGI connection (that's
covered by the integration test in test_websocket.py).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from app.websocket.connection_manager import ConnectionManager
from app.websocket.schemas import WSMessage


def _mock_websocket() -> AsyncMock:
    return AsyncMock()


class TestConnect:
    async def test_connect_accepts_and_tracks_the_connection(self) -> None:
        manager = ConnectionManager()
        ws = _mock_websocket()

        await manager.connect(ws)

        ws.accept.assert_awaited_once()
        assert manager.active_connection_count == 1


class TestDisconnect:
    async def test_disconnect_removes_a_tracked_connection(self) -> None:
        manager = ConnectionManager()
        ws = _mock_websocket()
        await manager.connect(ws)

        manager.disconnect(ws)

        assert manager.active_connection_count == 0

    async def test_disconnect_of_unknown_connection_does_not_raise(self) -> None:
        manager = ConnectionManager()
        ws = _mock_websocket()
        manager.disconnect(ws)  # never connected — should not raise
        assert manager.active_connection_count == 0


class TestBroadcast:
    async def test_broadcast_sends_to_all_connected_clients(self) -> None:
        manager = ConnectionManager()
        ws_a, ws_b = _mock_websocket(), _mock_websocket()
        await manager.connect(ws_a)
        await manager.connect(ws_b)

        await manager.broadcast(WSMessage(type="test", payload={"x": 1}))

        ws_a.send_json.assert_awaited_once()
        ws_b.send_json.assert_awaited_once()

    async def test_broadcast_with_no_connections_does_not_raise(self) -> None:
        manager = ConnectionManager()
        await manager.broadcast(WSMessage(type="test"))  # should not raise

    async def test_broadcast_message_envelope_shape(self) -> None:
        manager = ConnectionManager()
        ws = _mock_websocket()
        await manager.connect(ws)

        await manager.broadcast(WSMessage(type="ping_result", payload={"latency_ms": 12.5}))

        sent = ws.send_json.call_args.args[0]
        assert sent["type"] == "ping_result"
        assert sent["payload"] == {"latency_ms": 12.5}
        assert "timestamp" in sent

    async def test_broadcast_prunes_dead_connection_without_failing_others(self) -> None:
        manager = ConnectionManager()
        dead, alive = _mock_websocket(), _mock_websocket()
        dead.send_json.side_effect = RuntimeError("connection closed")
        await manager.connect(dead)
        await manager.connect(alive)

        await manager.broadcast(WSMessage(type="test"))  # must not raise

        alive.send_json.assert_awaited_once()
        assert manager.active_connection_count == 1  # dead one pruned


class TestSendPersonal:
    async def test_send_personal_delivers_to_the_specific_client_only(self) -> None:
        manager = ConnectionManager()
        ws_a, ws_b = _mock_websocket(), _mock_websocket()
        await manager.connect(ws_a)
        await manager.connect(ws_b)

        await manager.send_personal(ws_a, WSMessage(type="heartbeat"))

        ws_a.send_json.assert_awaited_once()
        ws_b.send_json.assert_not_awaited()

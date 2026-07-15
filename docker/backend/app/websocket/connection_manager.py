"""WebSocket connection manager.

Contract: owns the set of currently-connected dashboard clients and is
the ONLY place that calls `WebSocket.send_*`. Everything else that wants
to push a real-time update goes through the event bus
(`events/bus.py`) -> `websocket/event_forwarder.py` -> here, per the
brief's "Dashboard must update in real time. Never poll every second.
Push updates."
"""

from __future__ import annotations

from fastapi import WebSocket

from app.core.logging import get_logger
from app.websocket.schemas import WSMessage

logger = get_logger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        logger.info("websocket.connected", extra={"active_connections": len(self._connections)})

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)
        logger.info("websocket.disconnected", extra={"active_connections": len(self._connections)})

    @property
    def active_connection_count(self) -> int:
        return len(self._connections)

    async def broadcast(self, message: WSMessage) -> None:
        """Sends to every connected client.

        A dead connection encountered mid-broadcast is pruned rather
        than allowed to raise and abort the loop — one stale socket
        (client closed the tab without a clean disconnect handshake)
        must not block delivery to everyone else.
        """
        if not self._connections:
            return
        payload = message.model_dump(mode="json")
        stale: list[WebSocket] = []
        for connection in self._connections:
            try:
                await connection.send_json(payload)
            except Exception:
                stale.append(connection)
        for connection in stale:
            self.disconnect(connection)

    async def send_personal(self, websocket: WebSocket, message: WSMessage) -> None:
        await websocket.send_json(message.model_dump(mode="json"))

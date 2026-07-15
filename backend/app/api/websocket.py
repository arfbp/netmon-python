"""WebSocket endpoint.

Mounted at the app root as `/ws` (not under `/api/v1`) — matching the
Vite dev proxy already committed in Step 1's `frontend/vite.config.ts`
(`"/ws": { target: "ws://localhost:8000", ws: true }`). A WebSocket's
wire protocol (the `WSMessage.type` discriminator) can evolve without a
URL version bump the way a REST resource shape needs one, so this isn't
versioned under `/api/v1` the way `health.py` is.

This module's only job is accepting the connection, keeping it alive
with a heartbeat, and detecting disconnects. Fan-out to clients is the
connection manager's job (`websocket/connection_manager.py`); turning
domain events into outbound messages is the event forwarder's job
(`websocket/event_forwarder.py`). This endpoint doesn't do either.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.deps import ConnectionManagerDep, SettingsDep
from app.core.logging import get_logger
from app.websocket.schemas import WSMessage

logger = get_logger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, manager: ConnectionManagerDep, settings: SettingsDep
) -> None:
    await manager.connect(websocket)
    try:
        while True:
            try:
                # Blocks until the client sends something OR the
                # heartbeat interval elapses, whichever comes first.
                # Any inbound text currently just proves the connection
                # is alive — concrete client->server message types
                # (e.g. "subscribe to incident X") get added when a
                # feature actually needs bidirectional messages.
                await asyncio.wait_for(
                    websocket.receive_text(), timeout=settings.websocket.heartbeat_seconds
                )
            except TimeoutError:
                await manager.send_personal(websocket, WSMessage(type="heartbeat"))
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)

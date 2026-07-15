"""Bridges the event bus to connected WebSocket clients.

Contract: `register_event_forwarding()` is called once, at app startup
(`main.create_app`), subscribing a single wildcard handler that turns
every published domain event into a `WSMessage` and broadcasts it. This
is the one place `events/` and `websocket/` meet — monitors publishing
to the bus never import anything from `websocket/`, and the connection
manager never imports anything from `monitors/` or `events/schemas`.
"""

from __future__ import annotations

import dataclasses

from app.events.bus import EventBus
from app.websocket.connection_manager import ConnectionManager
from app.websocket.schemas import WSMessage


def _event_type_name(event: object) -> str:
    """`PingResultEvent` -> `"ping_result"` — the snake_case type
    discriminator the frontend switches on. Stripping the `Event` suffix
    keeps the wire format from repeating a word the `type` field's own
    existence already implies."""
    name = type(event).__name__
    if name.endswith("Event"):
        name = name[: -len("Event")]

    chars: list[str] = []
    for i, ch in enumerate(name):
        if ch.isupper() and i > 0:
            chars.append("_")
        chars.append(ch.lower())
    return "".join(chars)


def _event_payload(event: object) -> object:
    """Dataclass events (the expected case, per `events/schemas.py`)
    serialize via `dataclasses.asdict`; anything else falls back to
    `vars()` so a non-dataclass event doesn't crash forwarding outright,
    though every concrete event defined from Step 6 onward is expected
    to be a `DomainEvent` dataclass."""
    if dataclasses.is_dataclass(event) and not isinstance(event, type):
        return dataclasses.asdict(event)
    return vars(event)


def register_event_forwarding(bus: EventBus, manager: ConnectionManager) -> None:
    async def _forward(event: object) -> None:
        message = WSMessage(type=_event_type_name(event), payload=_event_payload(event))
        await manager.broadcast(message)

    bus.subscribe_all(_forward)

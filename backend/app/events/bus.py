"""In-process pub/sub event bus.

Contract: monitors (Step 6+) publish typed events here; consumers
(WebSocket forwarding — this step; the incident/alert services — later
steps) subscribe by event type, or via `subscribe_all()` for consumers
that need to relay every event regardless of type (the WebSocket layer).
This is the mechanism behind Step 1's stated rationale: a monitor
publishing `PingResultEvent` never needs to know the WebSocket layer or
the incident engine exist.

Concrete event types (`PingResultEvent`, `PacketLossDetectedEvent`, ...)
are defined by the monitor that produces them, starting Step 6 — this
module only provides the generic dispatch mechanism, not the event
vocabulary itself.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.core.logging import get_logger

logger = get_logger(__name__)

EventT = TypeVar("EventT")
Subscriber = Callable[[EventT], Awaitable[None]]


class EventBus:
    """Simple in-process async pub/sub, keyed by concrete event type.

    Not a message queue — no persistence, no delivery guarantees, no
    cross-process fan-out. That's the right tradeoff for a single-process
    local monitoring app; a multi-process deployment would swap this for
    Redis pub/sub or similar behind the same subscribe/publish interface,
    without callers needing to change.
    """

    def __init__(self) -> None:
        self._subscribers: dict[type, list[Subscriber]] = defaultdict(list)
        self._wildcard_subscribers: list[Subscriber] = []

    def subscribe(self, event_type: type[EventT], handler: Subscriber[EventT]) -> None:
        self._subscribers[event_type].append(handler)

    def subscribe_all(self, handler: Subscriber[object]) -> None:
        """Registers a handler invoked for every published event,
        regardless of type. Used by the WebSocket forwarding layer,
        which relays everything to connected clients without needing to
        know each concrete event type in advance."""
        self._wildcard_subscribers.append(handler)

    def unsubscribe(self, event_type: type[EventT], handler: Subscriber[EventT]) -> None:
        handlers = self._subscribers.get(event_type)
        if handlers and handler in handlers:
            handlers.remove(handler)

    async def publish(self, event: object) -> None:
        """Dispatches `event` to every type-specific subscriber for
        `type(event)` plus every wildcard subscriber. One subscriber
        raising does not prevent the others from receiving the event —
        a broken incident-engine handler must never take down real-time
        dashboard updates, or vice versa."""
        handlers = [*self._subscribers.get(type(event), []), *self._wildcard_subscribers]
        if not handlers:
            return

        for handler in handlers:
            try:
                await handler(event)
            except Exception:
                logger.exception(
                    "event_bus.subscriber_failed",
                    extra={"event_type": type(event).__name__, "handler": repr(handler)},
                )
